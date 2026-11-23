#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""极简版：不搬片段，只把「时间提醒」从 system 尾部挪到头部。

为什么换成这个：
  前几版想整块重排 prompt，每次都在切字符串，风险全在切错上，
  而收益也就每轮几分钱。现在只改一处拼接表达式，不动任何函数体。

  原样：  [人格][记忆][召回][最近][规则][工具][插件][Skip/Jump][气泡] + "\n\n" + 时间
  改后：  [时间] + "\n\n" + [人格][记忆][召回][最近][规则][工具][插件][Skip/Jump][气泡]

  时间虽然每轮都变，但它现在只在最开头变一次，
  后面那串内容仍然是完整连续的一大段，前缀缓存能从头吃到尾。
"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt")
MARK = "// [time-head]"

if not P.exists():
    print("[timehead] FAIL: file not found")
    sys.exit(1)

orig = P.read_text(encoding="utf-8")
if MARK in orig:
    print("[timehead] already patched")
    sys.exit(0)

src = orig

OLD_A = """            // 时间上下文无条件注入 与界面显示解耦
            val timeReminder = TimeReminderTransformer.buildReminder(messages)
            val systemWithTime = if (timeReminder != null) {
                system + "\\n\\n" + timeReminder
            } else system
"""

OLD_B = """            val timeReminder = if (assistant.enableTimeReminder) {
                TimeReminderTransformer.buildReminder(messages)
            } else null
            val systemWithTime = if (timeReminder != null) {
                system + "\\n\\n" + timeReminder
            } else system
"""

NEW = """            // [time-head] 时间顶到最前
            // 时间每轮都变，放在末尾会把前面整段前缀缓存作废；
            // 挪到最前之后，它后面那串固定内容仍是一条连续前缀。
            val timeReminder = TimeReminderTransformer.buildReminder(messages)
            val systemWithTime = when {
                timeReminder == null -> system
                system.isBlank() -> timeReminder
                else -> timeReminder + "\\n\\n" + system
            }
"""

if src.count(OLD_A) == 1:
    src = src.replace(OLD_A, NEW, 1)
    print("[timehead] matched OLD_A")
elif src.count(OLD_B) == 1:
    src = src.replace(OLD_B, NEW, 1)
    print("[timehead] matched OLD_B (switch removed)")
else:
    print("[timehead] FAIL: A=%d B=%d" % (src.count(OLD_A), src.count(OLD_B)))
    sys.exit(1)

checks = {
    "mark": MARK in src,
    "time_first": 'else -> timeReminder + "\\n\\n" + system' in src,
    "old_concat_gone": 'system + "\\n\\n" + timeReminder' not in src,
    "no_switch": "if (assistant.enableTimeReminder)" not in src,
    "translate_alive": "fun translateText(" in src,
    "generate_alive": "fun generateText(" in src,
    "build_string_once": src.count("val system = buildString {") == 1,
    "system_add_once": src.count("add(UIMessage.system(prompt = systemWithTime))") == 1,
    "limit_ctx": "addAll(messages.limitContext(assistant.contextMessageSize))" in src,
    "fun_count_same": src.count("\n    fun ") == orig.count("\n    fun "),
    "size_sane": abs(len(src) - len(orig)) < 2000,
}

for k, v in checks.items():
    print("[timehead] %-20s %s" % (k, "OK" if v else "FAIL"))
if not all(checks.values()):
    print("[timehead] ABORT (not written)")
    sys.exit(1)

P.write_text(src, encoding="utf-8", newline="")
print("[timehead] patched OK (%d -> %d bytes)" % (len(orig), len(src)))
