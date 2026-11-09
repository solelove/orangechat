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
 * 外层是否隐藏头像。
 *
 * 拆分模式下每个小气泡自己带一个头像，外层再画就重复了，所以隐藏；
 * 非拆分模式这条消息只有一个气泡，由外层画，不隐藏。
 */
internal fun shouldHideSideAvatar(
    isUser: Boolean,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    showAssistantBubble: Boolean,
    assistant: Assistant?,
): Boolean {
    if (!willSplitIntoBubbles(isUser, assistant)) return false
    return if (isUser) {
        showUserAvatar
    } else {
        showModelIcon && showAssistantBubble
    }
}

/**
 * 非文本段（图片/视频/音频/文档）的头像。
 *
 * 图片行自己带一个头像，所以只要图片行会画，外层就必须藏起来，
 * 否则一条带图的消息后面会出现两个头像。这里不再看拆分开关，
 * 因为不管拆不拆，图片行都有头像。
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
