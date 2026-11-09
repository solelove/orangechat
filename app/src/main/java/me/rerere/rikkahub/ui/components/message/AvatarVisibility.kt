/*
 * 橘瓣 OrangeChat
 * 头像归属规则
 *
 * 目标：每条消息、每个气泡、每个图片段，从头到尾只出现一个头像。
 *
 * 外层固定侧边头像什么时候画：
 *   - 消息本身是纯文本，且没开拆分
 * 其余情况外层一律不画，由具体块自己带：
 *   - 文本段：开了拆分 => 每个气泡自带头像
 *   - 图片/视频/音频/文档 段 => 那段自带
 *   - 混合消息（文字+图片）里的文字段 => 也要自己带，因为外层已经让位
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

/** 外层固定侧边头像要不要藏起来 */
internal fun shouldHideSideAvatar(isUser: Boolean, assistant: Assistant?): Boolean {
    return willSplitIntoBubbles(isUser, assistant)
}

/**
 * 文本段是否自带头像。
 * splitOrMixed = 开了拆分 或 这条消息里还有非文本段(外层已让位) 时，文本段自己带。
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

/** 图片/视频/音频/文档 旁边的头像，始终自带 */
internal fun partAvatarFor(
    isUser: Boolean,
    assistant: Assistant?,
    model: Model?,
    userAvatar: Avatar,
    userNickname: String,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
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
