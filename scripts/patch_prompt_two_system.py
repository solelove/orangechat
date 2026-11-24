#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 GenerationHandler 的 system 拆成「两条 system 消息」：

  messages[0] = 静态段：人格 + 代码块规则 + Skip + Jump + 气泡
  messages[1] = 动态段：记忆 + 外置召回 + 最近会话 + 工具 prompt + 插件

为什么：
  DeepSeek 的前缀缓存从第一个字符开始逐字连续匹配。原代码把 system 拼成
  **一条**消息，记忆/外置召回/最近会话/工具/插件全夹在里面，任何一处变化都会
  让这条消息从变化点往后全部失效。而 messages[0] 失效，等于后面整段历史都
  吃不到缓存。

  拆成两条后：静态段每轮完全一致 -> 永远命中；动态段怎么变都只影响自己。
  文字内容与顺序保持原样，只是中间切一刀，模型看到的东西不减少。

历史坑（务必保留这段血泪）：
  v1  anchor not found
  v2  区间切割命中多处，把 translateText 切掉 -> 编译失败
  v3  src.replace(old, new="") -> TypeError
  v4  grep 防呆误伤 docstring
  v5  数大括号假阳性
  v6  结束锚点用了补丁执行前的 timeReminder 形态
  v7  END 锚点带 "\\n"，文件可能是 CRLF -> 永远 hits=0
  v8  END 用了 master 才有的注释行，base 里不存在 -> hits=0
  v9  区间整段替换，成功
  v10 精确原文替换 + 断言；但等价性比对把块首 `val system = buildString {`
      也算了进去，它当然不在任何一段里 -> 误报 FAIL
  v11 等价性比对改为「先剔除块首块尾容器行」，其余行逐字比对

本版策略（v11）：
  1. 起始锚点 `val system = buildString {` 必须恰好命中 1 次；
  2. 结束锚点 `val timeReminder = ...` 用正则兼容两种形态，恰好命中 1 次；
  3. 各段用精确原文切出，任何一段找不到就中止；
  4. 等价性比对：原 block 去掉首行与末行大括号、去掉空行后，
     必须与「各段拼接后同样的处理」逐行一致；
  5. 所有断言通过才落盘。
"""
import pathlib
import re
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt")
MARK = "// [cache-two-system] "

if not P.exists():
    print("[two] FAIL: GenerationHandler.kt not found")
    sys.exit(1)

text = P.read_text(encoding="utf-8")

if MARK in text:
    print("[two] already patched, skip")
    sys.exit(0)

START_RE = re.compile(r"^[ \t]*val system = buildString \{[ \t]*\r?\n", re.M)
END_RE = re.compile(
    r"^[ \t]*val timeReminder = (?:if \(assistant\.enableTimeReminder\)|"
    r"TimeReminderTransformer\.buildReminder\(messages\))[^\r\n]*\r?\n",
    re.M,
)

starts = list(START_RE.finditer(text))
ends = list(END_RE.finditer(text))
if len(starts) != 1:
    print("[two] FAIL: start anchor hits=%d" % len(starts))
    sys.exit(1)
if len(ends) != 1:
    print("[two] FAIL: end anchor hits=%d" % len(ends))
    sys.exit(1)

s = starts[0].start()
e = ends[0].start()
if s >= e:
    print("[two] FAIL: start after end")
    sys.exit(1)

old = text[s:e]
print("[two] located block: %d chars" % len(old))

if "\n    fun " in old or "\n    private " in old:
    print("[two] FAIL: block spans a function boundary")
    sys.exit(1)

# ---------- 精确切段 ----------
PERSONA = """                val effectiveSystemPrompt =
                    if (assistant.allowConversationSystemPrompt && !conversationSystemPrompt.isNullOrBlank()) {
                        conversationSystemPrompt
                    } else {
                        assistant.systemPrompt
                    }
                if (effectiveSystemPrompt.isNotBlank()) {
                    append(effectiveSystemPrompt)
                }
"""

MEM = """                // 记忆
                if (assistant.enableMemory) {
                    appendLine()
                    append(buildMemoryPrompt(memories = memories))
                }
"""

CODEBLOCK = """                // 代码文件命名和ZIP打包功能说明
                appendLine()
                append(buildCodeBlockPrompt())
"""

TOOLS = """                // 工具prompt
                tools.forEach { tool ->
                    appendLine()
                    append(tool.systemPrompt(model, messages))
                }
"""

PLUGINS = """                // 插件提示词注入
                if (pluginPromptInjections.isNotEmpty()) {
                    pluginPromptInjections.forEach { injection ->
                        appendLine()
                        appendLine()
                        append(injection)
                    }
                }
"""

SKIP = """                // 允许跳过回复
                if (assistant.allowSkipReply) {
                    appendLine()
                    appendLine()
                    appendLine("## Skip Reply")
                    appendLine("If you determine that no reply is needed (e.g., the user's message doesn't require a response, or you have nothing meaningful to add), you may reply with exactly `[SKIP]` (without any other text). This message will be hidden from the user. Use this sparingly and only when truly appropriate.")
                }
"""

JUMP = """                // 屏幕跳转能力（AI总是可以跳转，不需要开关）
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
"""

BUBBLES = """                // 分气泡: 告知模型它自己能控制消息如何被拆成多个气泡
                if (assistant.splitBubbleByLine) {
                    appendLine()
                    appendLine()
                    appendLine("## Message Bubbles")
                    appendLine("Your reply will be automatically split into separate chat bubbles at every line break (\\\\n) you write, similar to how a person sends several short texts in a row instead of one long message. You are fully in control of this: write a line break whenever you want the previous thought/sentence to appear as its own bubble, and keep things on the same line when they belong together. Do not insert blank lines purely for spacing — every line break becomes a new bubble, so use them intentionally. Exception: line breaks inside fenced code blocks (```) and Markdown tables are preserved as-is and will NOT create new bubbles, since those must stay intact as a single block.")
                }
"""

RECENT = """                if (assistant.enableRecentChatsReference) {
                    appendLine()
                    append(buildRecentChatsPrompt(assistant, conversationRepo))
                }
"""

EXT_START = "                // 外置记忆库召回"
EXT_END_RE = re.compile(
    r"^[ \t]*\} catch \(e: Exception\) \{\r?\n"
    r"[ \t]*Log\.w\(TAG, \"External memory recall failed\", e\)\r?\n"
    r"[ \t]*\}\r?\n",
    re.M,
)

for name, seg in [
    ("persona", PERSONA), ("memory", MEM), ("codeblock", CODEBLOCK),
    ("tools", TOOLS), ("plugins", PLUGINS), ("skip", SKIP),
    ("jump", JUMP), ("bubbles", BUBBLES), ("recent", RECENT),
]:
    if old.count(seg) != 1:
        print("[two] FAIL: segment %s hits=%d" % (name, old.count(seg)))
        sys.exit(1)

hi = old.find(EXT_START)
if hi < 0 or old.count(EXT_START) != 1:
    print("[two] FAIL: external head hits=%d" % old.count(EXT_START))
    sys.exit(1)
me = EXT_END_RE.search(old, hi)
if not me:
    print("[two] FAIL: external tail not found")
    sys.exit(1)
EXTERNAL = old[hi:me.end()]
if "fun " in EXTERNAL:
    print("[two] FAIL: external segment spans too much")
    sys.exit(1)
print("[two] external segment: %d chars" % len(EXTERNAL))

# ---------- 等价性校验 ----------
# 原 block 的骨架行（不属于任何一段）：
#   首行 `val system = buildString {`  与末行 `}`（闭合 buildString）
# 处理办法：把所有行按 strip 后收集，剔除首行容器行与纯 "}" 行，再逐行比对。
def normalize(t):
    out = []
    for ln in t.splitlines():
        x = ln.strip()
        if not x:
            continue
        if x == "}":
            continue
        if x == "val system = buildString {":
            continue
        out.append(x)
    return out


segments = [PERSONA, MEM, EXTERNAL, RECENT, CODEBLOCK, TOOLS, PLUGINS, SKIP, JUMP, BUBBLES]
old_norm = normalize(old)
new_norm = normalize("".join(segments))

if old_norm != new_norm:
    missing = [x for x in old_norm if x not in new_norm]
    extra = [x for x in new_norm if x not in old_norm]
    print("[two] FAIL: content mismatch, missing=%r extra=%r" % (missing[:5], extra[:5]))
    sys.exit(1)
if len(old_norm) != len(new_norm):
    print("[two] FAIL: line count mismatch old=%d new=%d" % (len(old_norm), len(new_norm)))
    sys.exit(1)
print("[two] content equivalence OK (%d non-empty lines)" % len(old_norm))

# ---------- 拼装 ----------
STATIC = (
    "            // [cache-two-system] 静态段：每轮完全一致，单独作为 messages[0]，永远命中前缀缓存。\n"
    "            val staticSystem = buildString {\n"
    + PERSONA
    + "\n"
    + CODEBLOCK
    + "\n"
    + SKIP
    + "\n"
    + JUMP
    + "\n"
    + BUBBLES
    + "            }\n"
)

DYNAMIC = (
    "\n"
    "            // [cache-two-system] 动态段：记忆 / 外置召回 / 最近会话 / 工具 / 插件。\n"
    "            // 排在静态段之后单独成一条 system，怎么变都不影响前面那一条。\n"
    "            val dynamicSystem = buildString {\n"
    + MEM
    + "\n"
    + EXTERNAL
    + "\n"
    + RECENT
    + "\n"
    + TOOLS
    + "\n"
    + PLUGINS
    + "            }\n"
)

text = text[:s] + STATIC + DYNAMIC + text[e:]

# ---------- 落盘前断言 ----------
checks = {
    "mark": MARK in text,
    "static_sb": "val staticSystem = buildString {" in text,
    "dynamic_sb": "val dynamicSystem = buildString {" in text,
    "old_system_gone": "val system = buildString {" not in text,
    "translate_alive": "fun translateText(" in text,
    "generate_alive": "fun generateText(" in text,
    "throttle_alive": "throttleLatest(STREAM_UI_THROTTLE_MS)" in text,
    "codeblock_fn_alive": "private fun buildCodeBlockPrompt()" in text,
    "limit_intact": text.count("addAll(messages.limitContext(assistant.contextMessageSize))") == 1,
    "time_line_alive": "val timeReminder = " in text,
    "brace_balance": text.count("{") == text.count("}"),
}

si = text.find("val staticSystem = buildString {")
di = text.find("val dynamicSystem = buildString {")
checks["order_ok"] = si >= 0 and di > si

if si >= 0 and di > si:
    static_part = text[si:di]
    checks["persona_in_static"] = "assistant.systemPrompt" in static_part
    checks["codeblock_in_static"] = "buildCodeBlockPrompt()" in static_part
    checks["bubbles_in_static"] = "## Message Bubbles" in static_part
    checks["no_memory_in_static"] = "buildMemoryPrompt" not in static_part
    checks["no_tools_in_static"] = "tools.forEach" not in static_part
    checks["no_external_in_static"] = "External memory recall failed" not in static_part
    checks["no_recent_in_static"] = "buildRecentChatsPrompt" not in static_part

    dyn_part = text[di:]
    i_mem = dyn_part.find("buildMemoryPrompt(memories = memories)")
    i_rec = dyn_part.find("buildRecentChatsPrompt(assistant, conversationRepo)")
    checks["memory_first_in_dyn"] = 0 < i_mem < i_rec
    checks["external_in_dyn"] = "External memory recall failed" in dyn_part
    checks["recent_in_dyn"] = i_rec > 0
    checks["tools_in_dyn"] = "tools.forEach { tool ->" in dyn_part
    checks["plugins_in_dyn"] = "pluginPromptInjections.forEach" in dyn_part
else:
    for k in ["persona_in_static", "codeblock_in_static", "bubbles_in_static",
              "no_memory_in_static", "no_tools_in_static", "no_external_in_static",
              "no_recent_in_static", "memory_first_in_dyn", "external_in_dyn",
              "recent_in_dyn", "tools_in_dyn", "plugins_in_dyn"]:
        checks[k] = False

for k in checks:
    print("[two] %-24s %s" % (k, "OK" if checks[k] else "FAIL"))

if not all(checks.values()):
    print("[two] ABORT: 校验未通过，未写入文件")
    sys.exit(1)

P.write_text(text, encoding="utf-8", newline="")
print("[two] patched OK (%d bytes)" % len(text))
