/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.data.ai.transformers

import kotlinx.datetime.LocalDateTime
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toInstant
import kotlinx.datetime.toLocalDateTime
import me.rerere.ai.core.MessageRole
import me.rerere.ai.ui.UIMessage
import kotlin.time.Clock

/**
 * 时间提醒生成器
 *
 * 只产出 <time_reminder> 文本，由 GenerationHandler / 主动消息流程拼进系统提示，
 * 不往消息列表里插假消息。
 *
 * 关键点：时间一律取 Clock.System.now()，即每次请求真正发出时的当前时间。
 * 格式改成中文可读，避免模型把它当成一段英文噪声忽略掉。
 */
object TimeReminderTransformer : InputMessageTransformer {
    override suspend fun transform(
        ctx: TransformerContext,
        messages: List<UIMessage>,
    ): List<UIMessage> = messages

    /** 生成当前时间提醒文本；永远不为 null，保证每次都注入真实时间。 */
    fun buildReminder(messages: List<UIMessage>): String? {
        val tz = TimeZone.currentSystemDefault()
        val now = Clock.System.now().toLocalDateTime(tz)

        // 距上一条 user 消息过去多久：用真实 now 减去上一条 user 的 createdAt
        val userMessages = messages.filter { it.role == MessageRole.USER }
        val prevUser = userMessages.dropLast(1).lastOrNull()?.createdAt
        val prevAny = prevUser ?: messages.dropLast(1).lastOrNull()?.createdAt
        val gapSeconds = prevAny?.let {
            (now.toInstant(tz) - it.toInstant(tz)).inWholeSeconds
        }

        return buildTimeReminderText(gapSeconds?.takeIf { it > 60 }, now)
    }

    /**
     * 主动消息用：这条路没有"刚发的那条 user 消息"，
     * 用传入的上一条消息时间算间隔，保证主动发消息也知道现在几点、隔了多久。
     */
    fun buildReminderForProactive(lastMessageAt: LocalDateTime?): String {
        val tz = TimeZone.currentSystemDefault()
        val now = Clock.System.now().toLocalDateTime(tz)
        val gapSeconds = lastMessageAt?.let { prev ->
            (now.toInstant(tz) - prev.toInstant(tz)).inWholeSeconds
        }?.takeIf { it > 60 }
        return buildTimeReminderText(gapSeconds, now)
    }
}

/** 旧接口保留：把提醒以 user 消息形式注入（默认不再使用）。 */
internal fun applyTimeReminder(messages: List<UIMessage>): List<UIMessage> = messages

internal fun buildTimeReminderText(gapSeconds: Long?, time: LocalDateTime): String {
    val timeStr = String.format(
        java.util.Locale.US, "%04d年%02d月%02d日 %02d:%02d",
        time.year, time.monthNumber, time.dayOfMonth, time.hour, time.minute
    )
    val head = "<time_reminder>现在是 $timeStr ${weekNameOf(time)}"
    return if (gapSeconds != null) {
        "$head，距离上一条消息过去${formatGapChinese(gapSeconds)}。这是真实当前时间，不要凭感觉猜时间。</time_reminder>"
    } else {
        "$head。这是真实当前时间，不要凭感觉猜时间。</time_reminder>"
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

private fun formatGapChinese(seconds: Long): String {
    val m = seconds / 60
    val h = seconds / 3600
    val d = seconds / 86400
    return when {
        seconds < 60 -> "不到一分钟"
        m < 60 -> "$m 分钟"
        h < 24 -> {
            val restMin = m % 60
            if (restMin > 0) "$h 小时 $restMin 分钟" else "$h 小时"
        }
        else -> {
            val restHour = h % 24
            if (restHour > 0) "$d 天 $restHour 小时" else "$d 天"
        }
    }
}
