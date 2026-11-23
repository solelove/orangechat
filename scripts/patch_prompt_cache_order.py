#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 GenerationHandler 里的 system 拼接顺序改成「静态前缀 + 动态尾部」。

DeepSeek 的前缀缓存边界 = 从 messages 开头到第一处不同。
现在 generateInternal 里的顺序是：

    persona
    记忆 (buildMemoryPrompt)            <- 每轮可能变
    外置记忆库召回                       <- 每轮必变（关键词搜索 / 向量召回）
    最近会话 (buildRecentChatsPrompt)    <- updateAt 日期会变
    代码块规则 (buildCodeBlockPrompt)
    工具 systemPrompt                   <- 含 LocalDate.now()
    插件注入
    Skip Reply / Jump / Message Bubbles
    time_reminder                       <- 每轮必变

一变就把后面全废，实测只有最前面的 2.8K 命中。

改成：

    [静态] persona + 代码块规则 + Skip + Jump + 气泡
    [动态] 记忆 + 外置召回 + 最近会话 + 工具 prompt + 插件注入
    [动态] time_reminder（本来就在最后拼）

这样静态块整块能命中，动态块虽然不命中，但不会拖累前面。
"""
import io
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

# ---------- 定位 generateInternal 里的 system 构建块 ----------
start_anchor = "        val internalMessages = buildList {\n            val system = buildString {\n"
end_anchor = (
    "            // 时间上下文无条件注入 与界面显示解耦\n"
    "            val timeReminder = TimeReminderTransformer.buildReminder(messages)\n"
)

i = src.find(start_anchor)
j = src.find(end_anchor)
if i < 0 or j < 0 or j < i:
    print("[order] FAIL: anchor not found (i=%d j=%d)" % (i, j))
    sys.exit(1)

block_start = i + len(start_anchor)
old_body = src[block_start:j]

# 提取中间会被挪动的几个片段，保持原文本一字不动
def grab(pattern, tag):
    m = re.search(pattern, old_body, re.S)
    if not m:
        print("[order] FAIL: fragment not found: %s" % tag)
        sys.exit(1)
    return m.group(0)

# 1. 记忆块
frag_memory = grab(
    r"                // 记忆\n"
    r"                if \(assistant\.enableMemory\) \{.*?\n                \}\n\n",
    "memory",
)

# 2. 外置记忆库召回整段（含 try/catch）
frag_external = grab(
    r"                // 外置记忆库召回\n"
    r"                try \{.*?\n                \} catch \(e: Exception\) \{\n"
    r"                    Log\.w\(TAG, \"External memory recall failed\", e\)\n"
    r"                \}\n\n",
    "external",
)

# 3. 最近会话块
frag_recent = grab(
    r"                if \(assistant\.enableRecentChatsReference\) \{.*?\n                \}\n\n",
    "recent",
)

# 4. 代码块规则块
frag_codeblock = grab(
    r"                // 代码文件命名和ZIP打包功能说明\n"
    r"                appendLine\(\)\n"
    r"                append\(buildCodeBlockPrompt\(\)\)\n\n",
    "codeblock",
)

# 5. 工具 prompt 块
frag_tools = grab(
    r"                // 工具prompt\n"
    r"                tools\.forEach \{ tool ->.*?\n                \}\n\n",
    "tools",
)

# 6. 插件注入块
frag_plugins = grab(
    r"                // 插件提示词注入\n"
    r"                if \(pluginPromptInjections\.isNotEmpty\(\)\) \{.*?\n                \}\n\n",
    "plugins",
)

# 把被挪动的 6 段从原位置删除，剩下的就是纯静态段
static_rest = old_body
for frag in (frag_memory, frag_external, frag_recent, frag_codeblock, frag_tools, frag_plugins):
    if frag not in static_rest:
        print("[order] FAIL: fragment not in body")
        sys.exit(1)
    static_rest = static_rest.replace(frag, "", 1)

# 静态段里可能残留连续空行，压一下（只压 3 个以上连续空行）
static_rest = re.sub(r"\n{3,}", "\n\n", static_rest)

# 动态段：记忆 -> 外置召回 -> 最近会话 -> 工具 prompt -> 插件
dynamic_body = frag_memory + frag_external + frag_recent + frag_tools + frag_plugins

# 静态段保持原来的 append 到 `system` 这个 builder 上；动态段另起 buffer
# 注意：静态段里 codeblock 被移走了，但要保证它在静态段（它在原文里位于最近会话之后）
# 所以静态段顺序改成：persona(...) + codeblock + Skip/Jump/Bubbles
# 做法：把 codeblock 重新插到 Skip Reply 那段之前
skip_marker = "                // 允许跳过回复\n"
if skip_marker not in static_rest:
    print("[order] FAIL: skip marker not found")
    sys.exit(1)
static_rest = static_rest.replace(skip_marker, frag_codeblock + skip_marker, 1)

new_body = (
    "                // ---- 静态段：人格 + 代码块规则 + 开关说明（每轮内容一致，最长前缀能命中缓存）----\n"
    + static_rest
    + "                }\n"
    + "                // ---- 动态段：记忆 / 召回 / 最近会话 / 工具 prompt / 插件注入（每轮可能变，放最后）----\n"
    + "                val dynamicSystem = buildString {\n"
    + dynamic_body
    + "                }\n"
    + "                val system$ = if (dynamicSystem.isBlank()) system else system + \"\\n\\n\" + dynamicSystem\n"
)

new_body = HEADER + "\n" + new_body

# 原来后面是 `            }\n            // 时间上下文...`
src = src[:block_start] + new_body + src[j:]

# 时间提醒拼接里改用 system$（注意 $ 是 Kotlin 合法标识符字符，但为可读性用 systemFinal）
src = src.replace(
    "                val system$ = if (dynamicSystem.isBlank()) system else system + \"\\n\\n\" + dynamicSystem\n",
    "                val systemFinal = if (dynamicSystem.isBlank()) system else system + \"\\n\\n\" + dynamicSystem\n",
    1,
)

old_time = (
    "            val timeReminder = TimeReminderTransformer.buildReminder(messages)\n"
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
    print("[order] FAIL: time concat anchor not found")
    sys.exit(1)
src = src.replace(old_time, new_time, 1)

P.write_text(src, encoding="utf-8", newline="")

# ---------- 校验 ----------
checks = {
    "header": HEADER in src,
    "dynamic_block": "val dynamicSystem = buildString {" in src,
    "system_final": "val systemFinal = if (dynamicSystem.isBlank())" in src,
    "time_uses_final": "systemFinal + \"\\n\\n\" + timeReminder" in src,
    "memory_in_dynamic": "// ---- 动态段" in src,
    "codeblock_before_skip": (
        src.index("append(buildCodeBlockPrompt())") < src.index("// 允许跳过回复")
    ),
    "single_system_message": src.count("add(UIMessage.system(prompt = systemWithTime))") == 1,
}
bad = [k for k, v in checks.items() if not v]
for k, v in checks.items():
    print("[order] %-24s %s" % (k, "OK" if v else "FAIL"))
if bad:
    sys.exit(1)
print("[order] patched: static prefix + dynamic tail")
