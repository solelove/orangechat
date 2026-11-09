/*
 * 橘瓣 OrangeChat
 * 拆分气泡时外层头像隐藏逻辑
 */

package me.rerere.rikkahub.ui.components.message

import me.rerere.rikkahub.data.model.Assistant
import me.rerere.rikkahub.data.model.Avatar
import me.rerere.rikkahub.data.model.BubbleSplitMode
import me.rerere.ai.provider.Model

/**
 * 一条消息最终只有一个头像。
 *
 * 情况一：没开拆分 -> 外层 ChatMessage 画一个，气泡内部不画。
 * 情况二：开了拆分 -> 气泡内部每段各画一个，外层让位。
 * 情况三：有图片/视频/音频/文档 -> 由 PartRow 画，外层让位。
 *
 * assistant 为 null 时一律当没开拆分。
 */
internal fun willSplitIntoBubbles(isUser: Boolean, assistant: Assistant?): Boolean {
    if (assistant == null) return false
    val mode = if (isUser) assistant.effectiveUserSplitMode else assistant.bubbleSplitMode
    return mode.isEnabled
}

/** 外层是否隐藏头像 */
internal fun shouldHideSideAvatar(isUser: Boolean, assistant: Assistant?): Boolean {
    return willSplitIntoBubbles(isUser, assistant)
}

/**
 * 气泡内部是否需要自己画头像：只有开了拆分才画。
 * 未开拆分一律返回 null，交给外层。
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
    if (!willSplitIntoBubbles(isUser, assistant)) return null
    return if (isUser) {
        if (showUserAvatar) SegmentAvatarSpec.User(userAvatar, userNickname) else null
    } else {
        if (!showModelIcon || !showAssistantBubble) return null
        when {
            assistant != null && assistant.useAssistantAvatar -> SegmentAvatarSpec.AssistantAvatar(assistant)
            model != null -> SegmentAvatarSpec.Model(model.modelId)
            else -> null
        }
    }
}

/** 气泡实际使用的拆分模式 */
internal fun resolveSplitMode(isUser: Boolean, assistant: Assistant?): BubbleSplitMode {
    if (assistant == null) return BubbleSplitMode.NONE
    return if (isUser) assistant.effectiveUserSplitMode else assistant.bubbleSplitMode
}
