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


# ---------- 1. TimeReminderTransformer ----------
# createdAt 是 LocalDateTime，不是 Instant
TR_SRC = '''\ufeff/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.data.ai.transformers

import java.time.Duration
import java.time.LocalDateTime
import java.time.format.TextStyle
import java.util.Locale
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
        val userMessages = messages.filter { it.role == MessageRole.USER }
        val latest = userMessages.lastOrNull() ?: return null
        val curr = latest.createdAt
        val prev = userMessages.dropLast(1).lastOrNull()?.createdAt
        if (prev == null) return buildTimeReminderText(null, curr)
        val gapSeconds = Duration.between(prev, curr).seconds
        if (gapSeconds <= TIME_GAP_THRESHOLD_SECONDS) return null
        return buildTimeReminderText(gapSeconds, curr)
    }
}

/** 旧接口保留：把提醒以 user 消息形式注入（默认不再使用）。 */
internal fun applyTimeReminder(messages: List<UIMessage>): List<UIMessage> = messages

internal fun buildTimeReminderText(gapSeconds: Long?, time: LocalDateTime): String {
    val dayOfWeek = time.dayOfWeek.getDisplayName(TextStyle.FULL, Locale.getDefault())
    val timeStr = String.format(
        Locale.US, "%04d-%02d-%02d %02d:%02d",
        time.year, time.monthValue, time.dayOfMonth, time.hour, time.minute
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
'''

# ---------- 2. GenerationHandler ----------
GH_OLD_IMPORT = '''import me.rerere.rikkahub.data.ai.transformers.transforms'''
GH_NEW_IMPORT = '''import me.rerere.rikkahub.data.ai.transformers.transforms
import me.rerere.rikkahub.data.ai.transformers.TimeReminderTransformer'''

GH_OLD = '''            if (system.isNotBlank()) add(UIMessage.system(prompt = system))'''
GH_NEW = '''            val timeReminder = if (assistant.enableTimeReminder) {
                TimeReminderTransformer.buildReminder(messages)
            } else null
            val systemWithTime = if (timeReminder != null) {
                system + "\\n\\n" + timeReminder
            } else system
            if (systemWithTime.isNotBlank()) add(UIMessage.system(prompt = systemWithTime))'''

# ---------- 3. ChatList ----------
CL_OLD_IMPORT = '''import me.rerere.rikkahub.ui.hooks.ImeLazyListAutoScroller'''
CL_NEW_IMPORT = '''import me.rerere.rikkahub.ui.hooks.ImeLazyListAutoScroller
import java.time.Duration
import java.time.LocalDateTime'''

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
/** 微信式时间条：首条必显示，之后间隔 5 分钟以上才显示。 */
private fun showTimeHeader(nodes: List<MessageNode>, index: Int): Boolean {
    if (index == 0) return true
    val prev = nodes.getOrNull(index - 1) ?: return true
    val curr = nodes[index]
    val seconds = Duration.between(
        prev.currentMessage.createdAt,
        curr.currentMessage.createdAt,
    ).seconds
    return seconds >= 5 * 60 || seconds < 0
}

private fun formatTimeHeader(node: MessageNode, prevNode: MessageNode?): String {
    val t = node.currentMessage.createdAt
    val now = LocalDateTime.now()
    val hm = "%02d:%02d".format(t.hour, t.minute)
    if (t.toLocalDate() == now.toLocalDate()) return hm
    val prev = prevNode?.currentMessage?.createdAt
    if (prev != null && prev.toLocalDate() == t.toLocalDate()) return hm
    if (t.toLocalDate() == now.toLocalDate().minusDays(1)) return "昨天 $hm"
    val md = "${t.monthValue}月${t.dayOfMonth}日 $hm"
    return if (t.year == now.year) md else "${t.year}年$md"
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

TR.write_text(TR_SRC, encoding="utf-8")
print("[patch] TimeReminderTransformer rewritten")

gh = GH.read_text(encoding="utf-8")
gh = sub(gh, GH_OLD_IMPORT, GH_NEW_IMPORT, "generation-handler-import")
gh = sub(gh, GH_OLD, GH_NEW, "generation-handler-time")
GH.write_text(gh, encoding="utf-8")

cl = CL.read_text(encoding="utf-8")
cl = sub(cl, CL_OLD_IMPORT, CL_NEW_IMPORT, "chatlist-import")
cl = sub(cl, CL_OLD_ITEM, CL_NEW_ITEM, "chatlist-time-header-call")
cl = cl.rstrip() + "\n" + CL_APPEND
CL.write_text(cl, encoding="utf-8")

print("[patch] done")
