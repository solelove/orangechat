import sys

GH = "app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt"
TR = "app/src/main/java/me/rerere/rikkahub/data/ai/transformers/TimeReminderTransformer.kt"

# 1) GenerationHandler: 去掉 enableTimeReminder 开关判断，无条件注入
OLD_GH = """            val timeReminder = if (assistant.enableTimeReminder) {
                TimeReminderTransformer.buildReminder(messages)
            } else null
"""
NEW_GH = """            val timeReminder = TimeReminderTransformer.buildReminder(messages)
"""

# 2) TimeReminderTransformer: 去掉 1 小时间隔判断，每条消息都产出时间
OLD_TR = """        val currInstant = curr.toInstant(tz)
        val prevInstant = prev.toInstant(tz)
        val gapSeconds = (currInstant - prevInstant).inWholeSeconds
        if (gapSeconds <= TIME_GAP_THRESHOLD_SECONDS) return null
        return buildTimeReminderText(gapSeconds, curr)
"""
NEW_TR = """        val currInstant = curr.toInstant(tz)
        val prevInstant = prev.toInstant(tz)
        val gapSeconds = (currInstant - prevInstant).inWholeSeconds
        return buildTimeReminderText(gapSeconds, curr)
"""

def patch(path, old, new, tag):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    if new in src and old not in src:
        print(tag + ": ALREADY PATCHED")
        return
    if old not in src:
        print(tag + ": ANCHOR NOT FOUND")
        raise SystemExit(1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src.replace(old, new, 1))
    print(tag + ": PATCHED")

patch(GH, OLD_GH, NEW_GH, "GenerationHandler")
patch(TR, OLD_TR, NEW_TR, "TimeReminderTransformer")
print("ALL DONE")
