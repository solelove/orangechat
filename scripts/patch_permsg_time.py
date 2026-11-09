import re
import sys

PATH = "app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt"

OLD = """            val timeReminder = if (assistant.enableTimeReminder) {
                TimeReminderTransformer.buildReminder(messages)
            } else null
"""

NEW = """            val timeReminder = TimeReminderTransformer.buildReminder(messages)
"""

with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

if NEW in src and OLD not in src:
    print("ALREADY PATCHED")
elif OLD in src:
    src = src.replace(OLD, NEW, 1)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print("PATCHED OK")
else:
    print("ANCHOR NOT FOUND")
    sys.exit(1)
