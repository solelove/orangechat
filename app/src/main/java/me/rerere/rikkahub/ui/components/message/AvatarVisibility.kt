/*
 * 橘瓣 OrangeChat
 * 拆分气泡时外层头像隐藏逻辑
 */

package me.rerere.rikkahub.ui.components.message

import me.rerere.rikkahub.data.model.Assistant
import me.rerere.rikkahub.data.model.Avatar
import me.rerere.ai.provider.Model

/** 这条消息会不会被拆成多个小气泡 */
internal fun willSplitIntoBubbles(isUser: Boolean, assistant: Assistant?): Boolean {
    if (assistant == null) return false
    return if (isUser) {
        assistant.effectiveUserSplitMode.isEnabled
    } else {
        assistant.bubbleSplitMode.isEnabled
    }
}

/**
 * 外层头像永远画，不再因为"拆分成小气泡"而隐藏。
 *
 * 历史上有过一版让拆分后的小气泡自己带头像、外层藏掉，结果是图片行那份头像
 * 和文字气泡那份头像各自出现，一条消息后面跟着两个头像；而纯文本消息因为外层
 * 藏了、小气泡又只在特定模式才画，反而一个都没有。现在统一成：一条消息只由
 * 外层画一个头像，气泡内部和图片行都不再自己画。
 */
internal fun shouldHideSideAvatar(
    isUser: Boolean,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    showAssistantBubble: Boolean,
    assistant: Assistant?,
): Boolean = false

/** 非文本段（图片/视频/文档）不再单独带头像，交给外层统一画 */
internal fun segmentAvatarFor(
    isUser: Boolean,
    assistant: Assistant?,
    model: Model?,
    userAvatar: Avatar,
    userNickname: String,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    showAssistantBubble: Boolean,
): SegmentAvatarSpec? = null
