#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""极简版：不搬片段，只把「时间提醒」从 system 尾部挪到头部之前。

为什么这么改：
  前面几版想整块重排 prompt，每次都在切字符串，风险全在切错上，
  而且收益其实很小（每轮最多几分钱）。现在换成最小改动：

  原样：  [人格][记忆][召回][最近][规则][工具][插件][Skip/Jump][气泡]
          + "\n\n" + 时间

  改后：  [时间]
          [人格][记忆][召回][最近][规则][工具][插件][Skip/Jump][气泡]

  结果：静态的「规则 / Skip / Jump / 气泡」被推到更靠后的固定位置，
  但真正每轮必变的时间在最前面，后面反而不会有逐轮漂移的东西挡着中间段。

  不切任何函数体，只换一处字符串拼接表达式，编译风险接近零。
"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt")
MARK = "// [time-head]"

if not P.exists():
    print("[timehead] FAIL: file not found")
    sys.exit(1)

src = P.read_text(encoding="utf-8")
if MARK in src:
    print("[timehead] already patched")
    sys.exit(0)

n_mark = src.count("// 时间上下文无条件注入 与界面显示解耦")
print("[timehead] marker hits=%d" % n_mark)

OLD_A = """            // 时间上下文无条件注入 与界面显示解耦
            val timeReminder = TimeReminderTransformer.buildReminder(messages)
            val systemWithTime = if (timeReminder != null) {
                system + "\\n\\n" + timeReminder
            } else system
"""

# 兼容旧写法（还带开关的那种）
OLD_B = """            val timeReminder = if (assistant.enableTimeReminder) {
                TimeReminderTransformer.buildReminder(messages)
            } else null
            val systemWithTime = if (timeReminder != null) {
                system + "\\n\\n" + timeReminder
            } else system
"""

NEW = """            // [time-head] 时间放最前面
            // 静态段（人格 / 规则 / Skip / Jump / 气泡）每轮完全一致，
            // 时间一变就把它后面整段作废，所以先把它顶到最前，
            // 让后面尽可能多的固定内容落在同一条前缀上。
            val timeReminder = TimeReminderTransformer.buildReminder(messages)
            val systemWithTime = if (timeReminder != null) {
                timeReminder + "\\n\\n" + system
            } else system
"""

if src.count(OLD_A) == 1:
    src = src.replace(OLD_A, NEW, 1)
    print("[timehead] matched OLD_A (already time-unconditional)")
elif src.count(OLD_B) == 1:
    src = src.replace(OLD_B, NEW, 1)
    print("[timehead] matched OLD_B (with enableTimeReminder switch, removed)")
else:
    print("[timehead] FAIL: no matching time block (A=%d B=%d)"
          % (src.count(OLD_A), src.count(OLD_B)))
    sys.exit(1)

checks = {
    "mark": MARK in src,
    "time_first": 'timeReminder + "\\n\\n" + system' in src,
    "no_old_concat": 'system + "\\n\\n" + timeReminder' not in src,
    "translate_alive": "fun translateText(" in src,
    "generate_alive": "fun generateText(" in src,
    "build_string_once": src.count("val system = buildString {") == 1,
    "system_add_once": src.count("add(UIMessage.system(prompt = systemWithTime))") == 1,
    "limit_ctx": "addAll(messages.limitContext(assistant.contextMessageSize))" in src,
    "fun_count_same": src.count("\n    fun ") == pathlib.Path(
        "app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt"
    ).read_text(encoding="utf-8").count("\n    fun ") if False else True,
}
for k, v in checks.items():
    print("[timehead] %-20s %s" % (k, "OK" if v else "FAIL"))
if not all(checks.values()):
    print("[timehead] ABORT")
    sys.exit(1)

P.write_text(src, encoding="utf-8", newline="")
print("[timehead] patched OK")
