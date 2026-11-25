#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把时间提醒从 system 里挪到 messages 数组的最末尾（独立一条消息）。

为什么：
  DeepSeek 的前缀缓存从第一个字符开始逐字连续匹配。
  two-system 拆分之后结构是：
      messages[0] = 静态段（人格 + 代码块 + Skip/Jump + 气泡）—— 每轮完全一致
      messages[1] = 动态段（记忆 + 外置召回 + 最近会话 + 工具 + 插件）
  时间提醒带分钟数，每分钟都变。它一变，所在的那条消息就整条作废。

  v1 的做法是「追加到最后一条 user 消息里」。问题是：那条消息一旦被时间戳
  污染，下一轮它变成历史时，内容已经和当时发出去的不一样了（当时带的是旧时间，
  现在要发的是新时间），于是它永远匹配不上，每轮多脏一条，累积下去整段历史都补不回来。

  v2 改成独立一条消息，放在最后一条 user 之后：
      system0, system1, ..., 历史..., 最后一条 user, 时间
  时间只影响它自己那一条。前面整个前缀（两条 system + 全部历史 + 最后一条 user）
  都是干净的、逐字节不变的，可以持续命中。

必须跑在 patch_prompt_two_system.py 之后（依赖 staticSystem / dynamicSystem）。

安全设计：
  1. 三道锚点，每个必须恰好命中 1 次，且按顺序出现
  2. 锚点之间不允许出现 fun 定义（防跨函数切割）
  3. 替换完做断言，任何一项不过就不落盘
"""
import pathlib
import re
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt")
MARK = "// [time-tail]"

if not P.exists():
    print("[tail] FAIL: GenerationHandler.kt not found")
    sys.exit(1)

text = P.read_text(encoding="utf-8")

if MARK in text:
    print("[tail] already patched, skip")
    sys.exit(0)

# ---------- 锚点 1：timeReminder + systemWithTime 拼装块 ----------
A1_RE = re.compile(
    r"^[ \t]*val timeReminder = [^\r\n]*\r?\n"
    r"[ \t]*val systemWithTime = if \(timeReminder != null\) \{\r?\n"
    r"[ \t]*system \+ \"\\n\\n\" \+ timeReminder\r?\n"
    r"[ \t]*\} else system\r?\n",
    re.M,
)

# ---------- 锚点 2：add(UIMessage.system(prompt = systemWithTime)) ----------
A2_RE = re.compile(
    r"^[ \t]*if \(systemWithTime\.isNotBlank\(\)\) add\(UIMessage\.system\(prompt = systemWithTime\)\)\r?\n",
    re.M,
)

new = list(A1_RE.finditer(text))
sysm = list(A2_RE.finditer(text))

if len(new) != 1:
    print("[tail] FAIL: anchor1 (timeReminder block) hits=%d" % len(new))
    sys.exit(1)
if len(sysm) != 1:
    print("[tail] FAIL: anchor2 (add system) hits=%d" % len(sysm))
    sys.exit(1)

s1, e1 = new[0].span()
s2, e2 = sysm[0].span()

if not (s1 < e1 <= s2 < e2):
    print("[tail] FAIL: anchors out of order (a1=%d..%d a2=%d..%d)" % (s1, e1, s2, e2))
    sys.exit(1)

gap = text[e1:s2]
if "fun " in gap:
    print("[tail] FAIL: gap between anchors spans a function")
    sys.exit(1)

print("[tail] anchors OK: a1=%d bytes, gap=%d bytes" % (e1 - s1, len(gap)))

NEW_A1 = (
    "            // [time-tail] 时间提醒不进 system：它每分钟都变，\n"
    "            // 放在 system 里会把那条消息打碎，连带后面全部历史吃不到缓存。\n"
    "            val timeReminder = TimeReminderTransformer.buildReminder(messages)\n"
)

# 两条 system 分别 add：静态段永远稳定，动态段单独一条。
NEW_A2 = (
    "            if (staticSystem.isNotBlank()) add(UIMessage.system(prompt = staticSystem))\n"
    "            if (dynamicSystem.isNotBlank()) add(UIMessage.system(prompt = dynamicSystem))\n"
)

# 从后往前替换，避免偏移失效
text = text[:s2] + NEW_A2 + text[e2:]
text = text[:s1] + NEW_A1 + text[e1:]

# ---------- 锚点 3：limitContext 之后追加时间（独立一条消息） ----------
A3_RE = re.compile(
    r"^([ \t]*)addAll\(messages\.limitContext\(assistant\.contextMessageSize\)\)\r?\n",
    re.M,
)
lim = list(A3_RE.finditer(text))
if len(lim) != 1:
    print("[tail] FAIL: anchor3 (limitContext) hits=%d" % len(lim))
    sys.exit(1)

ind = lim[0].group(1)
TAIL = (
    "\n"
    + ind + "// [time-tail] 时间提醒单独一条消息，放在整个列表最末尾。\n"
    + ind + "// 不拼进任何 user 消息里：拼进去会让那条消息在下一轮变成历史时\n"
    + ind + "// 与当时发出的内容不一致（旧时间 vs 新时间），永远匹配不上缓存。\n"
    + ind + "// 独立一条则只弄脏它自己，前面两条 system + 全部历史 + 最后一条 user 全保住。\n"
    + ind + "if (!timeReminder.isNullOrBlank()) {\n"
    + ind + "    add(UIMessage.user(timeReminder))\n"
    + ind + "}\n"
)

text = text[:lim[0].end()] + TAIL + text[lim[0].end():]

# ---------- 校验 ----------
i_static_add = text.find("add(UIMessage.system(prompt = staticSystem))")
i_dyn_add = text.find("add(UIMessage.system(prompt = dynamicSystem))")
i_lim = text.find("addAll(messages.limitContext(assistant.contextMessageSize))")
i_tail = text.find("add(UIMessage.user(timeReminder))")

checks = {
    "mark": MARK in text,
    "systemWithTime_gone": "systemWithTime" not in text,
    "static_add_once": text.count("add(UIMessage.system(prompt = staticSystem))") == 1,
    "dynamic_add_once": text.count("add(UIMessage.system(prompt = dynamicSystem))") == 1,
    "no_bare_system_var": "prompt = system)" not in text,
    "time_line_alive": "val timeReminder = TimeReminderTransformer.buildReminder(messages)" in text,
    "tail_is_standalone": "add(UIMessage.user(timeReminder))" in text,
    "no_lastuser_copy": "val lastUserIndex = indexOfLast" not in text,
    "no_concat_into_parts": "UIMessagePart.Text(\"\\n\\n\" + timeReminder)" not in text,
    "limit_intact": text.count("addAll(messages.limitContext(assistant.contextMessageSize))") == 1,
    "translate_alive": "fun translateText(" in text,
    "generate_alive": "fun generateText(" in text,
    "throttle_alive": "throttleLatest(STREAM_UI_THROTTLE_MS)" in text,
    "codeblock_alive": "private fun buildCodeBlockPrompt()" in text,
    "static_alive": "val staticSystem = buildString {" in text,
    "dynamic_alive": "val dynamicSystem = buildString {" in text,
    "brace_balance": text.count("{") == text.count("}"),
    "order_ok": 0 <= i_static_add < i_dyn_add < i_lim < i_tail,
}

for k in checks:
    print("[tail] %-24s %s" % (k, "OK" if checks[k] else "FAIL"))

if not all(checks.values()):
    print("[tail] ABORT: 校验未通过，未写入文件")
    sys.exit(1)

P.write_text(text, encoding="utf-8", newline="")
print("[tail] patched OK (%d bytes)" % len(text))
