/*
 * 橘瓣 OrangeChat
 * 头像归属规则
 *
 * 目标：每条消息从头到尾只出现一个头像，而且位置固定。
 *
 * 规则按“拆分开关”一刀切，文字段和图片段不再各走各的：
 *   - 开了拆分：外层不画，文本段每段自带头像；图片段也自带。
 *   - 没开拆分：外层画唯一那一个侧边头像（纯文本、文字+图片都一样），
 *              文本段不画、图片段也不画。
 *
 * 之前出过的 bug：混合消息在没开拆分时，文本段拿到了 segmentAvatar，
 * 但 SplitBubbleColumn 在 mode.isEnabled=false 时根本不画头像，
 * 结果只有图片旁边有头像，文字旁边没有，看起来就是“对不齐”。
 */

package me.rerere.rikkahub.ui.components.message

import me.rerere.ai.provider.Model
import me.rerere.rikkahub.data.model.Assistant
import me.rerere.rikkahub.data.model.Avatar
import me.rerere.rikkahub.data.model.BubbleSplitMode

/** 这条消息会不会被拆成多个小气泡 */
internal fun willSplitIntoBubbles(isUser: Boolean, assistant: Assistant?): Boolean {
    if (assistant == null) return false
    return if (isUser) assistant.effectiveUserSplitMode.isEnabled else assistant.bubbleSplitMode.isEnabled
}

/** 文本气泡该用哪个拆分模式 */
internal fun resolveSplitMode(isUser: Boolean, assistant: Assistant?): BubbleSplitMode {
    if (assistant == null) return BubbleSplitMode.NONE
    return if (isUser) assistant.effectiveUserSplitMode else assistant.bubbleSplitMode
}

/** 外层固定侧边头像要不要藏起来：只由拆分开关决定 */
internal fun shouldHideSideAvatar(isUser: Boolean, assistant: Assistant?): Boolean {
    return willSplitIntoBubbles(isUser, assistant)
}

/**
 * 文本段是否自带头像：只有开了拆分才带。
 * 没开拆分时由外层统一画一个，文本段不要再画。
 */
internal fun segmentAvatarFor(
    isUser: Boolean,
    assistant: Assistant?,
    model: Model?,
    userAvatar: Avatar,
    userNickname: String,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    splitOrMixed: Boolean,
): SegmentAvatarSpec? {
    if (!willSplitIntoBubbles(isUser, assistant)) return null
    if (!splitOrMixed) return null
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

/**
 * 图片/视频/音频/文档 旁边的头像。
 * 开了拆分才自带；没开拆分时统一交给外层那一个侧边头像。
 */
internal fun partAvatarFor(
    isUser: Boolean,
    assistant: Assistant?,
    model: Model?,
    userAvatar: Avatar,
    userNickname: String,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
): SegmentAvatarSpec? {
    if (!willSplitIntoBubbles(isUser, assistant)) return null
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
