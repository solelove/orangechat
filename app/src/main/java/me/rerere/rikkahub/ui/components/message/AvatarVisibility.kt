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
 * 外层那个固定侧边头像要不要隐藏。
 * 只要这条消息里有会自己带头像的块（拆分气泡 或 图片/视频/音频/文档）
 * 外层就必须让位 否则会出现两个头像
 */
internal fun shouldHideSideAvatar(
    isUser: Boolean,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    showAssistantBubble: Boolean,
    assistant: Assistant?,
    hasNonTextParts: Boolean = false,
): Boolean {
    val split = willSplitIntoBubbles(isUser, assistant)
    val textWantsAvatar = if (split) {
        if (isUser) showUserAvatar else (showModelIcon && showAssistantBubble)
    } else {
        false
    }
    val partWantsAvatar = if (isUser) showUserAvatar else showModelIcon
    return textWantsAvatar || (hasNonTextParts && partWantsAvatar)
}

/** 非文本段（图片/视频/文档）也要跟着带头像 */
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
