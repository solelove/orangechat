import io

TR = "app/src/main/java/me/rerere/rikkahub/data/ai/transformers/TimeReminderTransformer.kt"
PM = "app/src/main/java/me/rerere/rikkahub/data/service/ProactiveMessageService.kt"
GEN = "app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt"


def load(p):
    return io.open(p, encoding="utf-8").read()


def save(p, s):
    io.open(p, "w", encoding="utf-8", newline="").write(s)


def rep(s, old, new, tag):
    if old not in s:
        raise SystemExit(tag + ": ANCHOR NOT FOUND")
    return s.replace(old, new, 1)


# ============ 一、GenerationHandler：时间注入改成无条件 ============
s = load(GEN)
if "无条件注入" in s:
    print("GEN already patched")
else:
    s = rep(s,
"""            val timeReminder = if (assistant.enableTimeReminder) {
                TimeReminderTransformer.buildReminder(messages)
            } else null""",
"""            // 时间上下文无条件注入 与界面显示解耦
            val timeReminder = TimeReminderTransformer.buildReminder(messages)""", "GEN1")
    save(GEN, s)
    print("GEN PATCHED")

# ============ 二、TimeReminderTransformer ============
s = load(TR)
if "buildReminderForProactive" in s:
    print("TR already patched")
else:
    s = rep(s,
"""    /** 生成当前时间提醒文本""",
"""    /**
     * 主动消息用：主动发起时没有刚发的那条 user 消息，
     * 直接传入上一条消息时间算间隔，保证主动发消息也知道现在几点、隔了多久。
     */
    fun buildReminderForProactive(lastMessageAt: LocalDateTime?): String {
        val tz = TimeZone.currentSystemDefault()
        val now = Clock.System.now().toLocalDateTime(tz)
        val gapSeconds = lastMessageAt?.let { prev ->
            (now.toInstant(tz) - prev.toInstant(tz)).inWholeSeconds
        }?.takeIf { it > 60 }
        return buildTimeReminderText(gapSeconds, now)
    }

    /** 生成当前时间提醒文本""", "TR1")

    s = rep(s,
"""        val prev = userMessages.dropLast(1).lastOrNull()?.createdAt""",
"""        val prev = userMessages.dropLast(1).lastOrNull()?.createdAt
            ?: messages.dropLast(1).lastOrNull()?.createdAt""", "TR2")

    s = rep(s,
"""    val timeStr = String.format(
        java.util.Locale.US, "%04d-%02d-%02d %02d:%02d",
        time.year, time.monthNumber, time.dayOfMonth, time.hour, time.minute
    )""",
"""    val timeStr = String.format(
        java.util.Locale.US, "%04d年%02d月%02d日 %02d:%02d",
        time.year, time.monthNumber, time.dayOfMonth, time.hour, time.minute
    )""", "TR3")

    save(TR, s)
    print("TR PATCHED")

# ============ 三、ProactiveMessageService ============
s = load(PM)
if "buildReminderForProactive" in s:
    print("PM already patched")
else:
    s = rep(s,
"isFromDeviceEvent: Boolean = false, deviceEventContext: String? = null): String {",
"isFromDeviceEvent: Boolean = false, deviceEventContext: String? = null, lastMessageAt: LocalDateTime? = null): String {", "PM1")

    s = rep(s,
"""                // 注入完整上下文（定位、前台app、app使用、通知、电量、健康等）
                if (!deviceEventContext.isNullOrBlank()) {
                    appendLine()
                    appendLine(deviceEventContext)
                }
            }
        }
    }""",
"""                // 注入完整上下文（定位、前台app、app使用、通知、电量、健康等）
                if (!deviceEventContext.isNullOrBlank()) {
                    appendLine()
                    appendLine(deviceEventContext)
                }
            }

            // 每条主动消息都带时间上下文：真实当前时间 + 距上一条消息多久
            appendLine()
            appendLine(TimeReminderTransformer.buildReminderForProactive(lastMessageAt))
        }
    }""", "PM2")

    s = rep(s,
"""                val systemPrompt = buildSystemPrompt(assistant, settings, idleMinutes, proactiveSetting.jumpIdleThresholdMinutes, isFromDeviceEvent, if (isFromDeviceEvent) deviceEventContext else contextStr)""",
"""                val lastMessageAt = conversation?.messageNodes?.lastOrNull()?.messages?.lastOrNull()?.createdAt
                val systemPrompt = buildSystemPrompt(assistant, settings, idleMinutes, proactiveSetting.jumpIdleThresholdMinutes, isFromDeviceEvent, if (isFromDeviceEvent) deviceEventContext else contextStr, lastMessageAt)""", "PM3")

    save(PM, s)
    print("PM PATCHED")

print("ALL DONE")
