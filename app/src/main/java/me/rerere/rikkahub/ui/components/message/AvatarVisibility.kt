/*
 * 橘瓣 OrangeChat
 * 拆分气泡时外层头像隐藏逻辑
 */

package me.rerere.rikkahub.ui.components.message

import me.rerere.rikkahub.data.model.Assistant
import me.rerere.rikkahub.data.model.Avatar
import me.rerere.rikkahub.data.model.BubbleSplitMode
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
 * 气泡内部（含图片行）是否自己带头像。
 *
 * 关键点：assistant 为 null 时（比如没绑助手、或者历史消息）气泡里照样会
 * 画头像，所以这里不能因为 assistant 为空就返回“不带头像”，否则外层又补
 * 画一个，就会出现一条消息两个头像。
 */
internal fun bubbleCarriesOwnAvatar(
    isUser: Boolean,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    showAssistantBubble: Boolean,
): Boolean {
    return if (isUser) {
        showUserAvatar
    } else {
        showModelIcon && showAssistantBubble
    }
}

/**
 * 外层是否隐藏头像：气泡自己带了，外层就让位。
 */
internal fun shouldHideSideAvatar(
    isUser: Boolean,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    showAssistantBubble: Boolean,
    assistant: Assistant?,
): Boolean = bubbleCarriesOwnAvatar(isUser, showUserAvatar, showModelIcon, showAssistantBubble)

/**
 * 非文本段（图片/视频/音频/文档）的头像。
 *
 * 图片行自己带一个头像，且不受拆分开关影响，所以外层一律要让位。
 */
internal fun segmentAvatarFor(
    isUser: Boolean,
    assistant: Assistant?,
    model: Model?,
    userAvatar: Avatar,
    userNickname: String,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    showAssistantBubble: Boolean,
): SegmentAvatarSpec? {
    return if (isUser) {
        if (showUserAvatar) SegmentAvatarSpec.User(userAvatar, userNickname) else null
    } else {
        if (!showModelIcon) return null
        when {
            assistant != null && assistant.useAssistantAvatar -> SegmentAvatarSpec.AssistantAvatar(assistant)
            model != null -> SegmentAvatarSpec.Model(model.modelId)
            else -> null
        }
    }
}

/** 气泡实际使用的拆分模式（assistant 为空时就是不拆分） */
internal fun resolveSplitMode(isUser: Boolean, assistant: Assistant?): BubbleSplitMode {
    if (assistant == null) return BubbleSplitMode.NONE
    return if (isUser) assistant.effectiveUserSplitMode else assistant.bubbleSplitMode
}
