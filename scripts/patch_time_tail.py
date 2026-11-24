#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把时间提醒从 system 里挪到 messages 数组的最末尾。

为什么：
  DeepSeek 的前缀缓存从第一个字符开始逐字连续匹配。
  静态/动态分段（v9）之后，system 的结构是：
      [静态段][动态段][time_reminder]
  time_reminder 里的分钟数每分钟都在变，它一变，system 这一整条消息
  就整条作废 —— 而 system 是 messages[0]，它作废 = 后面全部历史都吃不到缓存。

  所以把它剥出来，做成 messages 数组最后一条（role=user）的附加文本。
  这样它变的时候只影响自己那几十个字符，system 和整段历史全部保住。

安全设计（吃过太多次亏）：
  1. 三道锚点：systemWithTime 拼装块 / add(UIMessage.system(...)) / addAll(limitContext)
  2. 每道锚点必须恰好命中 1 次
  3. 三个锚点必须按顺序出现
  4. 替换区间里不允许出现 fun 定义
  5. 所有校验通过才落盘，任何一条不满足直接 exit 1
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

# ---------- 锚点 1：systemWithTime 拼装块 ----------
A1_RE = re.compile(
    r"^[ \t]*val timeReminder = [^\r\n]*\r?\n"
    r"^[ \t]*val systemWithTime = if \(timeReminder != null\) \{\r?\n"
    r"^[ \t]*system \+ \"\\n\\n\" \+ timeReminder\r?\n"
    r"^[ \t]*\} else system\r?\n",
    re.M,
)

# ---------- 锚点 2：add(UIMessage.system(prompt = systemWithTime)) ----------
A2_RE = re.compile(
    r"^[ \t]*if \(systemWithTime\.isNotBlank\(\)\) add\(UIMessage\.system\(prompt = systemWithTime\)\)\r?\n",
    re.M,
)

m1 = list(A1_RE.finditer(text))
m2 = list(A2_RE.finditer(text))

if len(m1) != 1:
    print("[tail] FAIL: anchor1 (systemWithTime block) hits=%d" % len(m1))
    sys.exit(1)
if len(m2) != 1:
    print("[tail] FAIL: anchor2 (add system) hits=%d" % len(m2))
    sys.exit(1)

s1, e1 = m1[0].span()
s2, e2 = m2[0].span()

if not (s1 < e1 <= s2 < e2):
    print("[tail] FAIL: anchors out of order")
    sys.exit(1)

between = text[e1:s2]
if "fun " in between:
    print("[tail] FAIL: fragment between anchors spans function boundary")
    sys.exit(1)

print("[tail] anchors located: a1=%d bytes, gap=%d bytes" % (e1 - s1, len(between)))

NEW_A1 = (
    "            // [time-tail] 时间提醒不放进 system。\n"
    "            // 它是每分钟都会变的，放进 messages[0] 会把整条 system 打碎、\n"
    "            // 连带着后面的全部历史都吃不到前缀缓存。改成追加到数组末尾，\n"
    "            // 它变的时候只影响自己那几十个字符。\n"
    "            val timeReminder = TimeReminderTransformer.buildReminder(messages)\n"
)

NEW_A2 = (
    "            if (system.isNotBlank()) add(UIMessage.system(prompt = system))\n"
)

# 先替换靠后的锚点，避免偏移失效
text = text[:s2] + NEW_A2 + text[e2:]
text = text[:s1] + NEW_A1 + text[e1:]

# ---------- 锚点 3：在 limitContext 之后追加末尾 user 消息 ----------
A3_RE = re.compile(
    r"^([ \t]*)addAll\(messages\.limitContext\(assistant\.contextMessageSize\)\)\r?\n",
    re.M,
)
m3 = list(A3_RE.finditer(text))
if len(m3) != 1:
    print("[tail] FAIL: anchor3 (limitContext) hits=%d" % len(m3))
    sys.exit(1)

indent = m3[0].group(1)
TAIL = (
    "\n"
    + indent
    + "// [time-tail] 时间提醒作为最后一段附在整条消息列表末尾。\n"
    + indent
    + "// 放在 system 里每分钟变一次会把整条 messages[0] 作废；\n"
    + indent
    + "// 放在末尾，静态段和全部历史都能继续命中前缀缓存。\n"
    + indent
    + "if (!system.isBlank() || internalSystemHasContent.compareAndSet(false, false)) {\n"
    + indent
    + "    // no-op, 保持结构清晰\n"
    + indent
    + "}\n"
)

# 真正的实现：把 timeReminder 追加到最后一个 user 消息（或新建一条）
REAL_TAIL = (
    "\n"
    + indent
    + "// [time-tail] 时间提醒附在 messages 数组的最末尾。\n"
    + indent
    + "// 它每分钟都变，放进 system（messages[0]）会把整条历史的前缀缓存全部作废。\n"
    + indent
    + "if (!timeReminder.isNullOrBlank()) {\n"
    + indent
    + "    val lastIdx = indexOfLast { it.role == MessageRole.USER }\n"
    + indent
    + "    if (lastIdx >= 0) {\n"
    + indent
    + "        val target = this[lastIdx]\n"
    + indent
    + "        this[lastIdx] = target.copy(\n"
    + indent
    + "            parts = target.parts + UIMessagePart.Text(\"\\n\\n\" + timeReminder)\n"
    + indent
    + "        )\n"
    + indent
    + "    } else {\n"
    + indent
    + "        add(UIMessage.user(timeReminder))\n"
    + indent
    + "    }\n"
    + indent
    + "}\n"
)

text = text[:m3[0].end()] + REAL_TAIL + text[m3[0].end():]

# ---------- 校验 ----------
checks = {
    "mark": MARK in text,
    "no_systemWithTime": "systemWithTime" not in text,
    "system_add_once": text.count("add(UIMessage.system(prompt = system))") == 1,
    "time_line_alive": "val timeReminder = " in text,
    "tail_append": "// [time-tail] 时间提醒附在 messages 数组的最末尾。" in text,
    "limit_intact": text.count("addAll(messages.limitContext(assistant.contextMessageSize))") == 1,
    "translate_alive": "fun translateText(" in text,
    "generate_alive": "fun generateText(" in text,
    "throttle_alive": "throttleLatest(STREAM_UI_THROTTLE_MS)" in text,
    "codeblock_alive": "private fun buildCodeBlockPrompt()" in text,
    "static_alive": "val staticSystem = buildString {" in text,
    "dynamic_alive": "val dynamicSystem = buildString {" in text,
    "brace_balance": text.count("{") == text.count("}"),
}

# 顺序：system 先 add，limitContext 后 addAll，再追加时间
i_sys = text.find("add(UIMessage.system(prompt = system))")
i_lim = text.find("addAll(messages.limitContext(assistant.contextMessageSize))")
i_tail = text.find("// [time-tail] 时间提醒附在 messages 数组的最末尾。")
checks["order_ok"] = 0 <= i_sys < i_lim < i_tail

for k, v in checks.items():
    print("[tail] %-22s %s" % (k, "OK" if v else "FAIL"))

if not all(checks.values()):
    print("[tail] ABORT: 校验未通过，未写入文件")
    sys.exit(1)

P.write_text(text, encoding="utf-8", newline="")
print("[tail] patched OK (%d bytes)" % len(text))
