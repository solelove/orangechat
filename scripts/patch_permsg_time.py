import io
import sys

P = "app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt"
s = io.open(P, encoding="utf-8").read()

OLD = (
    "            val timeReminder = TimeReminderTransformer.buildReminder(messages)\n"
    "            val systemWithTime = if (timeReminder != null) {\n"
    "                system + \"\\n\\n\" + timeReminder\n"
    "            } else system\n"
    "            if (systemWithTime.isNotBlank()) add(UIMessage.system(prompt = systemWithTime))\n"
    "            addAll(messages.limitContext(assistant.contextMessageSize))"
)

NEW = (
    "            val timeReminder = TimeReminderTransformer.buildReminder(messages)\n"
    "            val systemWithTime = if (timeReminder != null) {\n"
    "                system + \"\\n\\n\" + timeReminder\n"
    "            } else system\n"
    "            if (systemWithTime.isNotBlank()) add(UIMessage.system(prompt = systemWithTime))\n"
    "            addAll(\n"
    "                messages.limitContext(assistant.contextMessageSize).map { msg ->\n"
    "                    val stamp = \"<time_reminder>Current time: \" + String.format(\n"
    "                        java.util.Locale.US,\n"
    "                        \"%04d-%02d-%02d %02d:%02d\",\n"
    "                        msg.createdAt.year,\n"
    "                        msg.createdAt.monthNumber,\n"
    "                        msg.createdAt.dayOfMonth,\n"
    "                        msg.createdAt.hour,\n"
    "                        msg.createdAt.minute,\n"
    "                    ) + \"</time_reminder>\\n\"\n"
    "                    msg.copy(parts = listOf(UIMessagePart.Text(stamp)) + msg.parts)\n"
    "                }\n"
    "            )"
)

MARK = "msg.copy(parts = listOf(UIMessagePart.Text(stamp)) + msg.parts)"

if MARK in s:
    print("ALREADY PATCHED")
    sys.exit(0)

if OLD not in s:
    print("ANCHOR MISSING")
    idx = s.find("TimeReminderTransformer.buildReminder(messages)")
    if idx != -1:
        print("---- context around anchor ----")
        print(s[max(0, idx - 200):idx + 400])
    sys.exit(1)

s = s.replace(OLD, NEW, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("PATCHED OK")
