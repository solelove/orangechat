/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.data.ai.transformers

import kotlinx.datetime.LocalDateTime
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toLocalDateTime
import me.rerere.ai.core.MessageRole
import me.rerere.ai.ui.UIMessage
import kotlin.time.Clock

/**
 * 时间提醒生成器
 *
 * 只产出 <time_reminder> 文本，由 GenerationHandler 拼进系统提示，
 * 不往消息列表里插假消息。
 *
 * 关键点：时间一律取 Clock.System.now()，即每次请求真正发出时的当前时间。
 * 早期版本拿"最后一条 user 消息的 createdAt"当现在时间，一旦消息时间缺失
 * 或者最后一条 user 不是刚发的那条，就会算歪，所以改成实时取钟。
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
        val prev = userMessages.dropLast(1).lastOrNull()?.createdAt
        val gapSeconds = prev?.let {
            (now.toInstant(tz) - it.toInstant(tz)).inWholeSeconds
        } ?: 0L

        return buildTimeReminderText(gapSeconds.takeIf { it > 60 }, now)
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
