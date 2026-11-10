import io

TR = "app/src/main/java/me/rerere/rikkahub/data/ai/transformers/TimeReminderTransformer.kt"
PM = "app/src/main/java/me/rerere/rikkahub/data/service/ProactiveMessageService.kt"
AV = "app/src/main/java/me/rerere/rikkahub/ui/components/message/AvatarVisibility.kt"


def load(p):
    return io.open(p, encoding="utf-8").read()


def save(p, s):
    io.open(p, "w", encoding="utf-8", newline="").write(s)


def rep(s, old, new, tag):
    if old not in s:
        raise SystemExit(tag + ": ANCHOR NOT FOUND")
    return s.replace(old, new, 1)


# ================= 一、头像兼容修复（不改任何渲染逻辑） =================
s = load(AV)

if "fun resolveSplitMode" in s:
    print("AV already fixed")
else:
    s = rep(s,
"""internal fun shouldHideSideAvatar(
    isUser: Boolean,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    showAssistantBubble: Boolean,
    assistant: Assistant?,
): Boolean {""",
"""internal fun shouldHideSideAvatar(
    isUser: Boolean,
    showUserAvatar: Boolean = true,
    showModelIcon: Boolean = true,
    showAssistantBubble: Boolean = true,
    assistant: Assistant? = null,
): Boolean {""", "AV1")

    s = rep(s,
"""/** 非文本段（图片/视频/文档）在拆分模式下也要跟着带头像 */""",
"""/** 当前这条消息该用哪种气泡拆分模式；不拆分时返回 BubbleSplitMode.NONE */
internal fun resolveSplitMode(isUser: Boolean, assistant: Assistant?): BubbleSplitMode {
    if (assistant == null) return BubbleSplitMode.NONE
    return if (isUser) assistant.effectiveUserSplitMode else assistant.bubbleSplitMode
}

/** 非文本段（图片/视频/文档）在拆分模式下也要跟着带头像 */""", "AV2")

    s = rep(s,
"import me.rerere.rikkahub.data.model.Avatar",
"import me.rerere.rikkahub.data.model.Avatar\nimport me.rerere.rikkahub.data.model.BubbleSplitMode", "AV3")

    save(AV, s)
    print("AV FIXED")

# ================= 二、时间注入 · TimeReminderTransformer =================
s = load(TR)
if "buildReminderForProactive" in s:
    print("TR already patched")
else:
    s = rep(s,
"""    /** 生成当前时间提醒文本；永远不为 null，保证每次都注入真实时间。 */""",
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

    /** 生成当前时间提醒文本；永远不为 null，保证每次都注入真实时间。 */""", "TR1")

    s = rep(s,
"""        val prev = userMessages.dropLast(1).lastOrNull()?.createdAt""",
"""        val prev = userMessages.dropLast(1).lastOrNull()?.createdAt
            ?: messages.dropLast(1).lastOrNull()?.createdAt""", "TR2")

    s = rep(s,
"""internal fun buildTimeReminderText(gapSeconds: Long?, time: LocalDateTime): String {
    val dayOfWeek = time.dayOfWeek.name.lowercase().replaceFirstChar { it.uppercase() }
    val timeStr = String.format(
        java.util.Locale.US, "%04d-%02d-%02d %02d:%02d",
        time.year, time.monthNumber, time.dayOfMonth, time.hour, time.minute
    )
    val head = "<time_reminder>Current time: $dayOfWeek, $timeStr"
    return if (gapSeconds != null) {
        "$head (${formatGap(gapSeconds)} since last message)</time_reminder>"
    } else {
        "$head</time_reminder>"
    }
}

private fun formatGap(seconds: Long): String {
    return when {
        seconds < 3600 -> "${seconds / 60} min"
        seconds < 86400 -> "${seconds / 3600} h"
        else -> "${seconds / 86400} d"
    }
}""",
"""internal fun buildTimeReminderText(gapSeconds: Long?, time: LocalDateTime): String {
    val timeStr = String.format(
        java.util.Locale.US, "%04d年%02d月%02d日 %02d:%02d",
        time.year, time.monthNumber, time.dayOfMonth, time.hour, time.minute
    )
    val head = "<time_reminder>现在是 $timeStr ${weekNameOf(time)}"
    return if (gapSeconds != null) {
        "$head，距离上一条消息过去${formatGap(gapSeconds)}。这是真实当前时间，不要凭感觉猜。</time_reminder>"
    } else {
        "$head。这是真实当前时间，不要凭感觉猜。</time_reminder>"
    }
}

private fun weekNameOf(time: LocalDateTime): String = when (time.dayOfWeek.name) {
    "MONDAY" -> "星期一"
    "TUESDAY" -> "星期二"
    "WEDNESDAY" -> "星期三"
    "THURSDAY" -> "星期四"
    "FRIDAY" -> "星期五"
    "SATURDAY" -> "星期六"
    else -> "星期日"
}

private fun formatGap(seconds: Long): String {
    val m = seconds / 60
    val h = seconds / 3600
    val d = seconds / 86400
    return when {
        seconds < 60 -> "不到一分钟"
        m < 60 -> "${m} 分钟"
        h < 24 -> {
            val restMin = m % 60
            if (restMin > 0) "${h} 小时 ${restMin} 分钟" else "${h} 小时"
        }
        else -> {
            val restHour = h % 24
            if (restHour > 0) "${d} 天 ${restHour} 小时" else "${d} 天"
        }
    }
}""", "TR3")

    save(TR, s)
    print("TR PATCHED")

# ================= 三、时间注入 · ProactiveMessageService =================
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

            // 每条主动消息都带统一时间上下文：真实当前时间 + 距上一条消息多久
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
