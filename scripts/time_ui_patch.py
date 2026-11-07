# -*- coding: utf-8 -*-
"""时间提醒改为系统提示注入 + 聊天页微信式时间条。可重复执行。"""
import pathlib
import sys

ROOT = pathlib.Path(".")
TR = ROOT / "app/src/main/java/me/rerere/rikkahub/data/ai/transformers/TimeReminderTransformer.kt"
GH = ROOT / "app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt"
CL = ROOT / "app/src/main/java/me/rerere/rikkahub/ui/pages/chat/ChatList.kt"


def sub(text, old, new, tag):
    if text.count(old) != 1:
        print("[patch] locate failed: %s hits=%d" % (tag, text.count(old)))
        sys.exit(1)
    print("[patch] ok %s" % tag)
    return text.replace(old, new)


# ---------- 1. TimeReminderTransformer: 不再插入 user 消息，改为返回提示文本 ----------
TR_SRC = '''\ufeff/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.data.ai.transformers

import kotlin.time.Instant
import kotlinx.datetime.TimeZone
import kotlinx.datetime.toInstant
import me.rerere.ai.core.MessageRole
import me.rerere.ai.ui.UIMessage
import me.rerere.rikkahub.utils.toLocalDateTime
import java.time.ZoneId
import java.time.format.TextStyle
import java.util.Locale
import kotlin.time.toJavaInstant

private const val TIME_GAP_THRESHOLD_SECONDS = 3600L // 1 小时

/**
 * 时间提醒生成器
 *
 * 只产出 <time_reminder> 文本，由 GenerationHandler 拼进系统提示，
 * 不再往消息列表里插一条假的 user 消息（避免聊天界面出现空消息 / 打乱气泡分组）。
 */
object TimeReminderTransformer : InputMessageTransformer {
    override suspend fun transform(
        ctx: TransformerContext,
        messages: List<UIMessage>,
    ): List<UIMessage> = messages

    /**
     * 生成当前时间提醒文本；不需要注入时返回 null。
     */
    fun buildReminder(messages: List<UIMessage>): String? {
        val tz = TimeZone.currentSystemDefault()
        var firstUserFound = false
        var lastUserInstant: Instant? = null
        doc@ for (current in messages) {
            if (current.role != MessageRole.USER) continue
            val currInstant = current.createdAt.toInstant(tz)
            if (!firstUserFound) {
                firstUserFound = true
                lastUserInstant = currInstant
                break@doc
            }
        }
        val latest = messages.lastOrNull { it.role == MessageRole.USER } ?: return null
        val currInstant = latest.createdAt.toInstant(tz)
        val prevInstant = lastUserInstant
        val gapSeconds = prevInstant?.let { (currInstant - it).inWholeSeconds } ?: 0L
        if (prevInstant == null || gapSeconds > TIME_GAP_THRESHOLD_SECONDS) {
            return buildTimeReminderText(
                gapSeconds = if (prevInstant == null) null else gapSeconds,
                instant = currInstant,
            )
        }
        return null
    }
}

/** 旧接口保留：把提醒以 user 消息形式注入（默认不再使用）。 */
internal fun applyTimeReminder(messages: List<UIMessage>): List<UIMessage> = messages

internal fun buildTimeReminderText(gapSeconds: Long?, instant: Instant): String {
    val javaInstant = instant.toJavaInstant()
    val dayOfWeek = javaInstant.atZone(ZoneId.systemDefault()).dayOfWeek
        .getDisplayName(TextStyle.FULL, Locale.getDefault())
    val timeStr = javaInstant.toLocalDateTime()
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
'''

# ---------- 2. GenerationHandler: 系统提示里拼入时间提醒 ----------
GH_OLD = '''            if (system.isNotBlank()) add(UIMessage.system(prompt = system))'''
GH_NEW = '''            val timeReminder = if (assistant.enableTimeReminder) {
                me.rerere.rikkahub.data.ai.transformers.TimeReminderTransformer
                    .buildReminder(messages)
            } else null
            val systemWithTime = if (timeReminder != null) {
                "$system\\n\\n$timeReminder"
            } else system
            if (systemWithTime.isNotBlank()) add(UIMessage.system(prompt = systemWithTime))'''

# ---------- 3. ChatList: 微信式时间条 ----------
CL_OLD_ITEM = '''            ) { index, node ->
                Column {
                    ListSelectableItem('''

CL_NEW_ITEM = '''            ) { index, node ->
                Column {
                    if (showTimeHeader(displayNodes, index)) {
                        ChatTimeHeader(
                            text = formatTimeHeader(
                                node = node,
                                prevNode = displayNodes.getOrNull(index - 1),
                            )
                        )
                    }
                    ListSelectableItem('''

CL_APPEND = '''
/** 微信式时间条：首条必显示，之后间隔超过 5 分钟才显示。 */
private fun showTimeHeader(nodes: List<MessageNode>, index: Int): Boolean {
    if (index == 0) return true
    val prev = nodes.getOrNull(index - 1) ?: return true
    val curr = nodes[index]
    val prevTime = prev.currentMessage.createdAt
    val currTime = curr.currentMessage.createdAt
    return currTime.toEpochMilliseconds() - prevTime.toEpochMilliseconds() > 5 * 60 * 1000L
}

private fun formatTimeHeader(node: MessageNode, prevNode: MessageNode?): String {
    val now = kotlin.time.Clock.System.now()
        .toLocalDateTime(kotlinx.datetime.TimeZone.currentSystemDefault())
    val t = node.currentMessage.createdAt
    val sameDay = now.date == t.date
    val hm = "%02d:%02d".format(t.hour, t.minute)
    if (sameDay) return hm
    val prevDate = prevNode?.currentMessage?.createdAt?.date
    val yesterday = now.date.toEpochDays() - 1
    return when {
        prevDate != null && prevDate == t.date -> hm
        t.date.toEpochDays() == yesterday -> "昨天 $hm"
        now.date.year == t.date.year -> "${t.date.monthNumber}月${t.date.dayOfMonth}日 $hm"
        else -> "${t.date.year}年${t.date.monthNumber}月${t.date.dayOfMonth}日 $hm"
    }
}

@Composable
private fun ChatTimeHeader(text: String) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
            modifier = Modifier
                .clip(RoundedCornerShape(4.dp))
                .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f))
                .padding(horizontal = 8.dp, vertical = 2.dp),
        )
    }
}
'''

tr = TR.read_text(encoding="utf-8")
tr = TR_SRC
TR.write_text(tr, encoding="utf-8")
print("[patch] TimeReminderTransformer rewritten")

gh = GH.read_text(encoding="utf-8")
gh = sub(gh, GH_OLD, GH_NEW, "generation-handler-time")
GH.write_text(gh, encoding="utf-8")

cl = CL.read_text(encoding="utf-8")
cl = sub(cl, CL_OLD_ITEM, CL_NEW_ITEM, "chatlist-time-header-call")
cl = cl.rstrip() + "\n" + CL_APPEND
CL.write_text(cl, encoding="utf-8")

print("[patch] done")
