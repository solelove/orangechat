/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.data.ai.transformers

import kotlinx.datetime.LocalDateTime
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toInstant
import me.rerere.ai.core.MessageRole
import me.rerere.ai.ui.UIMessage

private const val TIME_GAP_THRESHOLD_SECONDS = 3600L // 1 小时

/**
 * 时间提醒生成器
 *
 * 只产出 <time_reminder> 文本，由 GenerationHandler 拼进系统提示，
 * 不再往消息列表里插一条假的 user 消息。
 */
object TimeReminderTransformer : InputMessageTransformer {
    override suspend fun transform(
        ctx: TransformerContext,
        messages: List<UIMessage>,
    ): List<UIMessage> = messages

    /** 生成当前时间提醒文本；不需要注入时返回 null。 */
    fun buildReminder(messages: List<UIMessage>): String? {
        val tz = TimeZone.currentSystemDefault()
        val userMessages = messages.filter { it.role == MessageRole.USER }
        val latest = userMessages.lastOrNull() ?: return null
        val curr = latest.createdAt
        val prev = userMessages.dropLast(1).lastOrNull()?.createdAt
        if (prev == null) return buildTimeReminderText(null, curr)

        val currInstant = curr.toInstant(tz)
        val prevInstant = prev.toInstant(tz)
        val gapSeconds = (currInstant - prevInstant).inWholeSeconds
        if (gapSeconds <= TIME_GAP_THRESHOLD_SECONDS) return null
        return buildTimeReminderText(gapSeconds, curr)
    }
}

/** 旧接口保留：把提醒以 user 消息形式注入（默认不再使用）。 */
internal fun applyTimeReminder(messages: List<UIMessage>): List<UIMessage> = messages

internal fun buildTimeReminderText(gapSeconds: Long?, time: LocalDateTime): String {
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
}
