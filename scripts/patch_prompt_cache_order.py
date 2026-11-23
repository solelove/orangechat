#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 GenerationHandler 的 system 拼接改成「静态前缀 + 动态尾部」。

背景：DeepSeek 前缀缓存按 messages 开头到第一处不同来算命中。
现在 generateInternal 的顺序是

    persona
    记忆                        <- 每轮变
    外置记忆库召回               <- 每轮必变
    最近会话                     <- updateAt 日期变
    代码块规则
    工具 systemPrompt            <- 含 LocalDate.now()
    插件注入
    Skip / Jump / 气泡            <- 这三段是静态的！
    time_reminder                <- 每轮必变

中间一变后面全废，实测只命中 2.8K / 833K ≈ 3.67%。

改成

    [静态] persona + 代码块规则 + Skip + Jump + 气泡
    [动态] 记忆 + 外置召回 + 最近会话 + 工具 prompt + 插件注入
    [动态] time_reminder（本来就在最后拼）

实现：不猜文本，按已知锚点定位，把 6 个动态段整段剪切出来，剩下的就是静态段，
再把静态段里被切走的 codeblock 插回 Skip 之前，最后拼 dynamicSystem。

注意基线（7b041d77）里时间那段还是旧的
    val timeReminder = if (assistant.enableTimeReminder) { ... } else null
所以这里同时把开关判断去掉（时间上下文与界面开关解耦），并改用 systemFinal。
"""
import pathlib
import re
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt")
HEADER = "// [cache-order] 静态段在前 动态段在后 提高 DeepSeek 前缀缓存命中率"

if not P.exists():
    print("[order] FAIL: GenerationHandler.kt not found")
    sys.exit(1)

src = P.read_text(encoding="utf-8")

if HEADER in src:
    print("[order] already patched")
    sys.exit(0)

# ---------------- 定位 system 构建块 ----------------
OPEN = "            val system = buildString {\n"
CLOSE = "\n            }\n            val timeReminder"

i = src.find(OPEN)
if i < 0:
    print("[order] FAIL: system builder not found")
    sys.exit(1)

body_start = i + len(OPEN)
j = src.find(CLOSE, body_start)
if j < 0:
    print("[order] FAIL: system builder end not found")
    sys.exit(1)

old_body = src[body_start:j]


def cut(pattern, tag):
    """把 old_body 里匹配的一段整段剪出来返回，并从 old_body 移除。"""
    global old_body
    m = re.search(pattern, old_body, re.S)
    if not m:
        print("[order] FAIL: fragment not found: %s" % tag)
        sys.exit(1)
    frag = m.group(0)
    old_body = old_body.replace(frag, "", 1)
    print("[order] cut %-10s %d chars" % (tag, len(frag)))
    return frag


# 1. 记忆
f_memory = cut(
    r"\n[ ]*// 记忆\n[ ]*if \(assistant\.enableMemory\) \{\n.*?\n[ ]*\}\n",
    "memory",
)

# 2. 外置记忆库召回（含 try/catch）
f_external = cut(
    r"\n[ ]*// 外置记忆库召回\n[ ]*try \{\n.*?\n[ ]*\} catch \(e: Exception\) \{\n"
    r"[ ]*Log\.w\(TAG, \"External memory recall failed\", e\)\n[ ]*\}\n",
    "external",
)

# 3. 最近会话
f_recent = cut(
    r"\n[ ]*if \(assistant\.enableRecentChatsReference\) \{\n.*?\n[ ]*\}\n",
    "recent",
)

# 4. 代码块规则
f_codeblock = cut(
    r"\n[ ]*// 代码文件命名和ZIP打包功能说明\n[ ]*appendLine\(\)\n"
    r"[ ]*append\(buildCodeBlockPrompt\(\)\)\n",
    "codeblock",
)

# 5. 工具 prompt
f_tools = cut(
    r"\n[ ]*// 工具prompt\n[ ]*tools\.forEach \{ tool ->\n.*?\n[ ]*\}\n",
    "tools",
)

# 6. 插件注入
f_plugins = cut(
    r"\n[ ]*// 插件提示词注入\n[ ]*if \(pluginPromptInjections\.isNotEmpty\(\)\) \{\n.*?\n[ ]*\}\n",
    "plugins",
)

# ---------------- 重建静态段 ----------------
# 静态段里 codeblock 已被剪掉，插回 Skip 之前
SKIP = "                // 允许跳过回复\n"
if SKIP not in old_body:
    print("[order] FAIL: skip marker not found in static rest")
    sys.exit(1)
old_body = old_body.replace(SKIP, f_codeblock + "\n" + SKIP, 1)

# 压掉因剪切留下的连续空行（3 个以上换行 -> 2 个）
static_body = re.sub(r"\n{3,}", "\n\n", old_body)
# 结尾统一收一个换行，方便拼接
static_body = static_body.rstrip() + "\n"

dynamic_body = (f_memory + f_external + f_recent + f_tools + f_plugins).strip("\n")
# 每个片段自身以换行结尾，拼接时逐个加缩进保持不变即可
dynamic_body = "\n".join(
    ("    " + line if line.strip() else line) for line in dynamic_body.split("\n")
)

new_block = (
    HEADER + "\n"
    + "            // ---- 静态段：人格 + 代码块规则 + 开关说明（每轮一致，前缀缓存能吃掉这一整块）----\n"
    + OPEN
    + static_body
    + "\n            }\n"
    + "            // ---- 动态段：记忆 / 外置召回 / 最近会话 / 工具 prompt / 插件注入（每轮可能变，放后面）----\n"
    + "            val dynamicSystem = buildString {\n"
    + dynamic_body + "\n"
    + "            }\n"
    + "            val systemFinal =\n"
    + "                if (dynamicSystem.isBlank()) system else system + \"\\n\\n\" + dynamicSystem\n"
)

src = src[:i] + new_block + src[j:]

# ---------------- 时间提醒：去开关 + 用 systemFinal ----------------
old_time = (
    "            val timeReminder = if (assistant.enableTimeReminder) {\n"
    "                TimeReminderTransformer.buildReminder(messages)\n"
    "            } else null\n"
    "            val systemWithTime = if (timeReminder != null) {\n"
    "                system + \"\\n\\n\" + timeReminder\n"
    "            } else system\n"
)
new_time = (
    "            val timeReminder = TimeReminderTransformer.buildReminder(messages)\n"
    "            val systemWithTime = if (timeReminder != null) {\n"
    "                systemFinal + \"\\n\\n\" + timeReminder\n"
    "            } else systemFinal\n"
)
if old_time not in src:
    print("[order] FAIL: time block anchor not found")
    sys.exit(1)
src = src.replace(old_time, new_time, 1)

P.write_text(src, encoding="utf-8", newline="")

# ---------------- 校验 ----------------
checks = {
    "header": HEADER in src,
    "dynamic_block": "val dynamicSystem = buildString {" in src,
    "system_final": "if (dynamicSystem.isBlank()) system else" in src,
    "time_uses_final": "systemFinal + \"\\n\\n\" + timeReminder" in src,
    "no_switch": "if (assistant.enableTimeReminder)" not in src,
    "codeblock_before_skip": (
        "append(buildCodeBlockPrompt())" in src
        and src.index("append(buildCodeBlockPrompt())") < src.index("// 允许跳过回复")
    ),
    "memory_after_dynamic": (
        "buildMemoryPrompt(memories = memories)" in src
        and src.index("buildMemoryPrompt(memories = memories)")
        > src.index("val dynamicSystem = buildString {")
    ),
    "tools_after_dynamic": (
        "tools.forEach { tool ->" in src
        and src.index("tools.forEach { tool ->") > src.index("val dynamicSystem = buildString {")
    ),
    "single_system_add": src.count("add(UIMessage.system(prompt = systemWithTime))") == 1,
    "limit_context_intact": "addAll(messages.limitContext(assistant.contextMessageSize))" in src,
    "build_string_balanced": src.count("val system = buildString {") == 1,
}
for k, v in checks.items():
    print("[order] %-24s %s" % (k, "OK" if v else "FAIL"))
if not all(checks.values()):
    sys.exit(1)
print("[order] patched OK: static prefix + dynamic tail")
