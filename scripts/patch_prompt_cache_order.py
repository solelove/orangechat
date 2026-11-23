#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 GenerationHandler 的 system 拼接改成「静态前缀 + 动态尾部」。

上一版为什么炸：用 `\\n            }\\n            val timeReminder` 找尾声，
这个片段在文件里不止一处匹配，find 取到的是靠前的那一个，结果把
translateText 等后面的代码一起切掉了，编译报 Unresolved reference 'translateText'。

这一版不再做区间切割。全部改成「精确原文替换」：

  1) 六段动态片段（记忆 / 外置召回 / 最近会话 / 工具 prompt / 插件注入）
     各自用完整原文匹配，原地删掉，收集到 dynamic_parts。
  2) 代码块规则段整段剪出来（它要留在静态段，但要挪到 Skip 之前）。
  3) 在原位置插入 dynamicSystem 构建块，内容就是收集到的 1)+工具prompt+插件。
  4) 时间提醒去开关 + 改用 systemFinal。

每一步都断言「命中次数 == 1」，任何一个不稳就直接 abort，
不再有“切到别的地方还不知道”的可能。
"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt")
MARK = "// [cache-order]"
if not P.exists():
    print("[order] FAIL: GenerationHandler.kt not found")
    sys.exit(1)

src = P.read_text(encoding="utf-8")
if MARK in src:
    print("[order] already patched")
    sys.exit(0)


def drop(old, tag):
    """精确删除 old（必须恰好出现一次），返回被删掉的原文。"""
    global src
    n = src.count(old)
    if n != 1:
        print("[order] FAIL %s: hits=%d" % (tag, n))
        sys.exit(1)
    src = src.replace(old, new="", count=1)
    print("[order] drop %-10s %d chars" % (tag, len(old)))
    return old


def swap(old, new, tag):
    global src
    n = src.count(old)
    if n != 1:
        print("[order] FAIL %s: hits=%d" % (tag, n))
        sys.exit(1)
    src = src.replace(old, new, 1)
    print("[order] swap %-10s ok" % tag)


# ---------------- 1. 剪出六段 ----------------
# 记忆
f_memory = drop(
    """                // 记忆
                if (assistant.enableMemory) {
                    appendLine()
                    append(buildMemoryPrompt(memories = memories))
                }
""",
    "memory",
)

# 最近会话
f_recent = drop(
    """                if (assistant.enableRecentChatsReference) {
                    appendLine()
                    append(buildRecentChatsPrompt(assistant, conversationRepo))
                }
""",
    "recent",
)

# 代码块规则（保留在静态段，但位置挪到 Skip 之前）
f_codeblock = drop(
    """                // 代码文件命名和ZIP打包功能说明
                appendLine()
                append(buildCodeBlockPrompt())
""",
    "codeblock",
)

# 工具 prompt
f_tools = drop(
    """                // 工具prompt
                tools.forEach { tool ->
                    appendLine()
                    append(tool.systemPrompt(model, messages))
                }
""",
    "tools",
)

# 插件注入
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

# 外置记忆库召回：整段很长，用首尾锚点定位后精确删除
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
if src.count(f_external) != 1:
    print("[order] FAIL external: not unique")
    sys.exit(1)
src = src.replace(f_external, "", 1)
print("[order] drop %-10s %d chars" % ("external", len(f_external)))

# ---------------- 2. 静态段里把代码块插回 Skip 之前 ----------------
SKIP = "                // 允许跳过回复\n"
swap(SKIP, f_codeblock + "\n" + SKIP, "codeblock-reinsert")

# ---------------- 3. 在原位置插入 dynamicSystem ----------------
# 静态段落尾：重建并插入到 `            }\n            val timeReminder`
ANCHOR = (
    "            }\n"
    "            val timeReminder = if (assistant.enableTimeReminder) {\n"
)
if src.count(ANCHOR) != 1:
    print("[order] FAIL anchor: hits=%d" % src.count(ANCHOR))
    sys.exit(1)

# 动态段内容：记忆 + 外置召回 + 最近会话 + 工具 prompt + 插件
dyn_inner = "".join([f_memory, f_external, f_recent, f_tools, f_plugins])
dyn_inner = dyn_inner.rstrip() + "\n"

# 统一缩进 +4（从 buildString 顶层挪进 dynamicSystem 里）
dyn_inner = "\n".join(
    ("    " + ln if ln.strip() else ln) for ln in dyn_inner.split("\n")
)

NEW_TAIL = (
    "            }\n"
    "            // [cache-order] 静态段在上 动态段在下\n"
    "            // 静态块（人格 + 代码块规则 + Skip/Jump/气泡）每轮完全一致，\n"
    "            // 动态块（记忆 / 外置召回 / 最近会话 / 工具 prompt / 插件注入）每轮可能变，\n"
    "            // 排在静态块之后就不会把前缀缓存的命中段打碎。\n"
    "            val dynamicSystem = buildString {\n"
    + dyn_inner +
    "            }\n"
    "            val systemFinal =\n"
    "                if (dynamicSystem.isBlank()) system else system + \"\\n\\n\" + dynamicSystem\n"
    "            val timeReminder = TimeReminderTransformer.buildReminder(messages)\n"
)
src = src.replace(ANCHOR, NEW_TAIL, 1)

# ---------------- 4. 时间提醒拼到 systemFinal 上 ----------------
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

P.write_text(src, encoding="utf-8", newline="")

# ---------------- 校验 ----------------
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
}

if "append(buildCodeBlockPrompt())" in src and "// 允许跳过回复" in src:
    checks["codeblock_before_skip"] = (
        src.index("append(buildCodeBlockPrompt())") < src.index("// 允许跳过回复")
    )
else:
    checks["codeblock_before_skip"] = False

if "val dynamicSystem = buildString {" in src:
    d = src.index("val dynamicSystem = buildString {")
    checks["memory_in_dynamic"] = (
        "buildMemoryPrompt(memories = memories)" in src
        and src.index("buildMemoryPrompt(memories = memories)") > d
    )
    checks["tools_in_dynamic"] = (
        "tools.forEach { tool ->" in src and src.index("tools.forEach { tool ->") > d
    )
    checks["external_in_dynamic"] = (
        "External memory recall failed" in src
        and src.index("External memory recall failed") > d
    )
else:
    checks["memory_in_dynamic"] = False
    checks["tools_in_dynamic"] = False
    checks["external_in_dynamic"] = False

# 括号平衡粗检：整个文件 { 与 } 数量应一致
checks["braces_balanced"] = src.count("{") == src.count("}")

for k, v in checks.items():
    print("[order] %-24s %s" % (k, "OK" if v else "FAIL"))
if not all(checks.values()):
    print("[order] ABORT: keep original file untouched is not possible now, but CI will fail loudly")
    sys.exit(1)
print("[order] patched OK: static prefix + dynamic tail")
