#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 GenerationHandler 的 system 拼接改成「静态前缀段 + 动态尾段」。

为什么：
  DeepSeek 的前缀缓存从第一个字符开始逐字匹配。原代码 system 是一个大
  buildString 平铺，记忆 / 外置召回 / 最近会话 / 工具 prompt / 插件注入这些
  「每轮都可能变」的内容夹在中间，任何一处变化都会让它后面的全部内容失效，
  命中率因此只有 15~20%。

  改成：静态段（人格 + 代码块规则 + Skip/Jump/气泡）排最前且每轮完全一致，
  动态段全部后置。前缀能吃到静态段全部，命中率大幅提高。

历史坑：
  v1  anchor not found
  v2  区间切割命中多处，把 translateText 切掉 -> 编译失败
  v3  src.replace(old, new="") -> TypeError
  v4  grep 防呆误伤 docstring
  v5  数大括号假阳性
  v6  结束锚点用了补丁执行前的 timeReminder 形态（workflow 正则已改过它）
  v7  END 锚点带 "\\n"，但文件可能是 CRLF 行尾 -> 永远 hits=0

本版策略（v8）：
  1. 锚点一律不带换行符，只匹配行内容，行尾用正则统一吃 \\r?\\n；
  2. 起始锚点 + 结束锚点定位唯一一段，断言各自恰好出现 1 次；
  3. 断言起点在终点前，且区间内不含函数定义（防止跨函数切割）；
  4. 整段替换，不做局部 patch；
  5. 所有校验通过才落盘，任一项失败直接退出且不写文件。
"""
import pathlib
import re
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt")
MARK = "// [cache-order] "

if not P.exists():
    print("[split] FAIL: GenerationHandler.kt not found")
    sys.exit(1)

text = P.read_text(encoding="utf-8")

if MARK in text:
    print("[split] already patched, skip")
    sys.exit(0)

# 只匹配行内容，不依赖行尾（文件可能是 LF 也可能是 CRLF）
START_RE = re.compile(r"^[ \t]*val system = buildString \{[ \t]*\r?\n", re.M)
# 结束边界：这行注释在打补丁前后都不变，且 workflow 的正则不会碰它
END_RE = re.compile(r"^[ \t]*// 时间上下文无条件注入[^\r\n]*\r?\n", re.M)

m_starts = list(START_RE.finditer(text))
m_ends = list(END_RE.finditer(text))

if len(m_starts) != 1:
    print("[split] FAIL: start anchor hits=%d (expect 1)" % len(m_starts))
    sys.exit(1)
if len(m_ends) != 1:
    print("[split] FAIL: end anchor hits=%d (expect 1)" % len(m_ends))
    sys.exit(1)

s = m_starts[0].start()
e = m_ends[0].start()
if s >= e:
    print("[split] FAIL: start anchor after end anchor")
    sys.exit(1)

old_block = text[s:e]

if "\n    fun " in old_block or "\n    private " in old_block:
    print("[split] FAIL: fragment spans function boundary (len=%d)" % len(old_block))
    sys.exit(1)

for need in [
    "val effectiveSystemPrompt =",
    "buildMemoryPrompt(memories = memories)",
    "buildCodeBlockPrompt()",
    "## Message Bubbles",
    "tools.forEach { tool ->",
]:
    if need not in old_block:
        print("[split] FAIL: expected fragment missing: %s" % need)
        sys.exit(1)

print("[split] located block: %d chars" % len(old_block))

# 新代码统一用 LF，项目本身是 LF
NEW_BLOCK = '''            // [cache-order] 静态前缀段：每轮完全一致的固定内容排在最前，
            // 这样前缀缓存能吃满这一整段。
            val staticSystem = buildString {
                val effectiveSystemPrompt =
                    if (assistant.allowConversationSystemPrompt && !conversationSystemPrompt.isNullOrBlank()) {
                        conversationSystemPrompt
                    } else {
                        assistant.systemPrompt
                    }
                if (effectiveSystemPrompt.isNotBlank()) {
                    append(effectiveSystemPrompt)
                }

                // 代码文件命名和ZIP打包功能说明（静态规则，放到前缀段）
                appendLine()
                append(buildCodeBlockPrompt())

                // 允许跳过回复
                if (assistant.allowSkipReply) {
                    appendLine()
                    appendLine()
                    appendLine("## Skip Reply")
                    appendLine("If you determine that no reply is needed (e.g., the user's message doesn't require a response, or you have nothing meaningful to add), you may reply with exactly `[SKIP]` (without any other text). This message will be hidden from the user. Use this sparingly and only when truly appropriate.")
                }

                // 屏幕跳转能力（AI总是可以跳转，不需要开关）
                if (true) {
                    appendLine()
                    appendLine()
                    appendLine("## 屏幕跳转能力")
                    appendLine("你可以在回复末尾追加 [JUMP] 标记（单独一行）来把聊天界面拉到用户屏幕最前面。")
                    appendLine("适用场景：")
                    appendLine("- 用户说要去别的应用，你觉得需要把用户拉回来时")
                    appendLine("- 你觉得接下来的内容需要用户立即看到时")
                    appendLine("不适用场景：")
                    appendLine("- 一般闲聊不需要跳转")
                    appendLine("- 用户正在跟你正常对话时不需要跳转")
                    appendLine("[JUMP] 标记不会展示给用户，仅用于触发屏幕跳转。")
                }

                // 分气泡: 告知模型它自己能控制消息如何被拆成多个气泡
                if (assistant.splitBubbleByLine) {
                    appendLine()
                    appendLine()
                    appendLine("## Message Bubbles")
                    appendLine("Your reply will be automatically split into separate chat bubbles at every line break (\\\\n) you write, similar to how a person sends several short texts in a row instead of one long message. You are fully in control of this: write a line break whenever you want the previous thought/sentence to appear as its own bubble, and keep things on the same line when they belong together. Do not insert blank lines purely for spacing — every line break becomes a new bubble, so use them intentionally. Exception: line breaks inside fenced code blocks (```) and Markdown tables are preserved as-is and will NOT create new bubbles, since those must stay intact as a single block.")
                }
            }

            // [cache-order] 动态尾段：记忆 / 外置召回 / 最近会话 / 工具 / 插件
            // 这些内容每轮都可能变化，排在静态段之后，就不会把前面的命中段打碎。
            val dynamicSystem = buildString {
                // 记忆
                if (assistant.enableMemory) {
                    appendLine()
                    append(buildMemoryPrompt(memories = memories))
                }
'''

EXT_HEAD = "// 外置记忆库召回"
EXT_TAIL_RE = re.compile(r"^[ \t]*Log\.w\(TAG, \"External memory recall failed\"[^\r\n]*\r?\n[ \t]*\}[ \t]*\r?\n", re.M)

if old_block.count(EXT_HEAD) != 1:
    print("[split] FAIL: external head hits=%d" % old_block.count(EXT_HEAD))
    sys.exit(1)
h = old_block.index(EXT_HEAD)
# 从 EXT_HEAD 所在行首开始截，保留原有缩进
line_start = old_block.rfind("\n", 0, h) + 1
mt = EXT_TAIL_RE.search(old_block, h)
if not mt:
    print("[split] FAIL: external tail not found")
    sys.exit(1)
external_seg = old_block[line_start:mt.end()]
if "fun " in external_seg:
    print("[split] FAIL: external segment spans too much")
    sys.exit(1)
print("[split] external segment: %d chars" % len(external_seg))

# 外置段里的缩进要保持和 dynamicSystem 对齐（原代码就在同一层级，直接用）
NEW_BLOCK += external_seg

NEW_BLOCK += '''
                if (assistant.enableRecentChatsReference) {
                    appendLine()
                    append(buildRecentChatsPrompt(assistant, conversationRepo))
                }

                // 工具prompt
                tools.forEach { tool ->
                    appendLine()
                    append(tool.systemPrompt(model, messages))
                }

                // 插件提示词注入
                if (pluginPromptInjections.isNotEmpty()) {
                    pluginPromptInjections.forEach { injection ->
                        appendLine()
                        appendLine()
                        append(injection)
                    }
                }
            }

            val system = if (dynamicSystem.isBlank()) {
                staticSystem
            } else {
                staticSystem + "\\n\\n" + dynamicSystem
            }

'''

text = text[:s] + NEW_BLOCK + text[e:]

checks = {
    "mark": MARK in text,
    "static_sb": "val staticSystem = buildString {" in text,
    "dynamic_sb": "val dynamicSystem = buildString {" in text,
    "combine": "if (dynamicSystem.isBlank()) {" in text,
    "old_concat_gone": "system + \"\\n\\n\" + timeReminder" in text,
    "translate_alive": "fun translateText(" in text,
    "generate_alive": "fun generateText(" in text,
    "throttle_alive": "throttleLatest(STREAM_UI_THROTTLE_MS)" in text,
    "codeblock_fn_alive": "private fun buildCodeBlockPrompt()" in text,
    "single_system_add": text.count("add(UIMessage.system(prompt = systemWithTime))") == 1,
    "limit_intact": "addAll(messages.limitContext(assistant.contextMessageSize))" in text,
    "time_comment_alive": "// 时间上下文无条件注入" in text,
}

si = text.find("val staticSystem = buildString {")
di = text.find("val dynamicSystem = buildString {")
checks["order_ok"] = si >= 0 and di > si

if di >= 0:
    checks["memory_in_dyn"] = text.find("buildMemoryPrompt(memories = memories)", di) > di
    checks["recent_in_dyn"] = text.find("buildRecentChatsPrompt(assistant, conversationRepo)", di) > di
    checks["tools_in_dyn"] = text.find("tools.forEach { tool ->", di) > di
    checks["plugins_in_dyn"] = text.find("pluginPromptInjections.forEach", di) > di
    checks["external_in_dyn"] = text.find("External memory recall failed", di) > di
else:
    checks["memory_in_dyn"] = False
    checks["recent_in_dyn"] = False
    checks["tools_in_dyn"] = False
    checks["plugins_in_dyn"] = False
    checks["external_in_dyn"] = False

if si >= 0 and di > si:
    static_part = text[si:di]
    checks["codeblock_in_static"] = "buildCodeBlockPrompt()" in static_part
    checks["no_memory_in_static"] = "buildMemoryPrompt" not in static_part
    checks["no_tools_in_static"] = "tools.forEach" not in static_part
else:
    checks["codeblock_in_static"] = False
    checks["no_memory_in_static"] = False
    checks["no_tools_in_static"] = False

# 括号配平（Kotlin 文件整体级，允许字符串里有括号，这里只做粗检）
if text.count("{") != text.count("}"):
    checks["brace_balance"] = False
else:
    checks["brace_balance"] = True

for k, v in checks.items():
    print("[split] %-22s %s" % (k, "OK" if v else "FAIL"))

if not all(checks.values()):
    print("[split] ABORT: 校验未通过，未写入文件")
    sys.exit(1)

P.write_text(text, encoding="utf-8", newline="")
print("[split] patched OK (%d bytes)" % len(text))
