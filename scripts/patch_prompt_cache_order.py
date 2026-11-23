#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 GenerationHandler 的 system 拼接改成「静态前缀 + 动态尾部」。

历史坑：
  v1  按 anchor 文本定位，基线里没有那段文本 -> anchor not found。
  v2  用 `}\\nval timeReminder` 找尾声，片段命中多处，把 translateText 切掉 -> 编译失败。
  v3  drop() 里写成 src.replace(old, new="") -> TypeError: replace() takes at least 2
      positional arguments。python 的 str.replace 不接受 new= 关键字。

这一版：全部用「精确原文替换」，每次断言命中次数 == 1，
写入前先做全部校验，校验不过就 sys.exit(1) 且不落盘（保持原文件干净）。
"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt")
MARK = "// [cache-order]"

if not P.exists():
    print("[order] FAIL: GenerationHandler.kt not found")
    sys.exit(1)

src_orig = P.read_text(encoding="utf-8")
if MARK in src_orig:
    print("[order] already patched")
    sys.exit(0)

src = src_orig


def drop(old, tag):
    """精确删除 old（必须恰好出现一次），返回被删掉的原文。"""
    global src
    n = src.count(old)
    if n != 1:
        print("[order] FAIL %s: hits=%d" % (tag, n))
        sys.exit(1)
    src = src.replace(old, "", 1)
    print("[order] drop %-12s %d chars" % (tag, len(old)))
    return old


def swap(old, new, tag):
    global src
    n = src.count(old)
    if n != 1:
        print("[order] FAIL %s: hits=%d" % (tag, n))
        sys.exit(1)
    src = src.replace(old, new, 1)
    print("[order] swap %-12s ok" % tag)


# ---------------- 1. 剪出各动态片段 ----------------
f_memory = drop(
    """                // 记忆
                if (assistant.enableMemory) {
                    appendLine()
                    append(buildMemoryPrompt(memories = memories))
                }
""",
    "memory",
)

f_recent = drop(
    """                if (assistant.enableRecentChatsReference) {
                    appendLine()
                    append(buildRecentChatsPrompt(assistant, conversationRepo))
                }
""",
    "recent",
)

f_codeblock = drop(
    """                // 代码文件命名和ZIP打包功能说明
                appendLine()
                append(buildCodeBlockPrompt())
""",
    "codeblock",
)

f_tools = drop(
    """                // 工具prompt
                tools.forEach { tool ->
                    appendLine()
                    append(tool.systemPrompt(model, messages))
                }
""",
    "tools",
)

f_plugins = drop(
    """                // 插件提示词注入
                if (pluginPromptInjections.isNotEmpty()) {
                    pluginPromptInjections.forEach { injection ->
                        appendLine()
                        appendLine()
                        append(injection)
                    }
                }
""",
    "plugins",
)

# 外置记忆库召回：整段很长，用首尾锚点定位
EXT_HEAD = "                // 外置记忆库召回\n                try {\n"
EXT_TAIL = (
    "                } catch (e: Exception) {\n"
    "                    Log.w(TAG, \"External memory recall failed\", e)\n"
    "                }\n"
)
h = src.find(EXT_HEAD)
if h < 0:
    print("[order] FAIL external: head not found")
    sys.exit(1)
t = src.find(EXT_TAIL, h)
if t < 0:
    print("[order] FAIL external: tail not found")
    sys.exit(1)
f_external = src[h:t + len(EXT_TAIL)]
if f_external.count("val system = buildString {") > 0 or "fun " in f_external:
    print("[order] FAIL external: fragment spans too much")
    sys.exit(1)
if src.count(f_external) != 1:
    print("[order] FAIL external: not unique")
    sys.exit(1)
src = src.replace(f_external, "", 1)
print("[order] drop %-12s %d chars" % ("external", len(f_external)))

# ---------------- 2. 代码块规则插回静态段的 Skip 之前 ----------------
SKIP = "                // 允许跳过回复\n"
swap(SKIP, f_codeblock + "\n" + SKIP, "codeblock")

# ---------------- 3. 静态段收尾 + 动态段 ----------------
ANCHOR = (
    "            }\n"
    "            val timeReminder = if (assistant.enableTimeReminder) {\n"
)
if src.count(ANCHOR) != 1:
    print("[order] FAIL anchor: hits=%d" % src.count(ANCHOR))
    sys.exit(1)

dyn_inner = "".join([f_memory, f_external, f_recent, f_tools, f_plugins])
dyn_inner = dyn_inner.rstrip() + "\n"
# 缩进 +4（从 buildString 顶层挪进 dynamicSystem 内层）
dyn_inner = "\n".join(
    ("    " + ln if ln.strip() else ln) for ln in dyn_inner.split("\n")
)

NEW_TAIL = (
    "            }\n"
    "            // [cache-order] 静态段在上 动态段在下\n"
    "            // 静态块（人格 + 代码块规则 + Skip/Jump/气泡）每轮完全一致，可吃到前缀缓存；\n"
    "            // 动态块（记忆 / 外置召回 / 最近会话 / 工具 prompt / 插件注入）每轮可能变，\n"
    "            // 放到静态块之后，就不会把前面的命中段打碎。\n"
    "            val dynamicSystem = buildString {\n"
    + dyn_inner +
    "            }\n"
    "            val systemFinal =\n"
    "                if (dynamicSystem.isBlank()) system else system + \"\\n\\n\" + dynamicSystem\n"
    "            val timeReminder = TimeReminderTransformer.buildReminder(messages)\n"
)
src = src.replace(ANCHOR, NEW_TAIL, 1)

# ---------------- 4. 时间提醒拼到 systemFinal ----------------
swap(
    """            val systemWithTime = if (timeReminder != null) {
                system + "\\n\\n" + timeReminder
            } else system
""",
    """            val systemWithTime = if (timeReminder != null) {
                systemFinal + "\\n\\n" + timeReminder
            } else systemFinal
""",
    "time-concat",
)

# ---------------- 校验（通过才落盘）----------------
checks = {
    "mark": MARK in src,
    "dynamic_block": "val dynamicSystem = buildString {" in src,
    "system_final": "if (dynamicSystem.isBlank()) system else" in src,
    "time_uses_final": "systemFinal + \"\\n\\n\" + timeReminder" in src,
    "no_switch": "if (assistant.enableTimeReminder)" not in src,
    "translate_text_alive": "fun translateText(" in src,
    "generate_text_alive": "fun generateText(" in src,
    "build_string_once": src.count("val system = buildString {") == 1,
    "single_system_add": src.count("add(UIMessage.system(prompt = systemWithTime))") == 1,
    "limit_context_intact": "addAll(messages.limitContext(assistant.contextMessageSize))" in src,
    "braces_balanced": src.count("{") == src.count("}"),
}

if "append(buildCodeBlockPrompt())" in src and "// 允许跳过回复" in src:
    checks["codeblock_before_skip"] = (
        src.index("append(buildCodeBlockPrompt())") < src.index("// 允许跳过回复")
    )
else:
    checks["codeblock_before_skip"] = False

d = src.find("val dynamicSystem = buildString {")
checks["memory_in_dynamic"] = d >= 0 and src.find("buildMemoryPrompt(memories = memories)", d) > d
checks["tools_in_dynamic"] = d >= 0 and src.find("tools.forEach { tool ->", d) > d
checks["external_in_dynamic"] = d >= 0 and src.find("External memory recall failed", d) > d

for k, v in checks.items():
    print("[order] %-24s %s" % (k, "OK" if v else "FAIL"))
if not all(checks.values()):
    print("[order] ABORT: 校验未通过，未写入文件")
    sys.exit(1)

P.write_text(src, encoding="utf-8", newline="")
print("[order] patched OK: static prefix + dynamic tail (%d -> %d bytes)" % (len(src_orig), len(src)))
