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

/** 拆分后小气泡自己带头像，外层这个不用再画 */
internal fun shouldHideSideAvatar(
    isUser: Boolean,
    showUserAvatar: Boolean = true,
    showModelIcon: Boolean = true,
    showAssistantBubble: Boolean = true,
    assistant: Assistant?,
): Boolean {
    val split = willSplitIntoBubbles(isUser, assistant)
    if (!split) return false
    return if (isUser) {
        showUserAvatar
    } else {
        showModelIcon && showAssistantBubble
    }
}

/** 当前消息该用哪种拆分模式；没开就是 NONE */
internal fun resolveSplitMode(isUser: Boolean, assistant: Assistant?): BubbleSplitMode {
    if (assistant == null) return BubbleSplitMode.NONE
    return if (isUser) assistant.effectiveUserSplitMode else assistant.bubbleSplitMode
}

/** 非文本段（图片/视频/文档）在拆分模式下也要跟着带头像 */
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
    if (!willSplitIntoBubbles(isUser, assistant)) return null
    return if (isUser) {
        if (showUserAvatar) SegmentAvatarSpec.User(userAvatar, userNickname) else null
    } else {
        if (!showAssistantBubble || !showModelIcon) return null
        when {
            assistant != null && assistant.useAssistantAvatar -> SegmentAvatarSpec.AssistantAvatar(assistant)
            model != null -> SegmentAvatarSpec.Model(model.modelId)
            else -> null
        }
    }
}
