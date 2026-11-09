/*
 * 橘瓣 OrangeChat
 * 拆分气泡 / 非文本块 的头像归属规则
 *
 * 规则一句话：谁能自己带头像，谁就带；不能的交给外层，保证永远只有一个。
 *  - 文本消息：开了拆分 => 每个气泡自带头像，外层不画
 *              没开拆分 => 外层画唯一一个
 *  - 含图片/视频/音频/文档的消息：那段自己带头像，外层一律不画
 */

package me.rerere.rikkahub.ui.components.message

import me.rerere.ai.provider.Model
import me.rerere.rikkahub.data.model.Assistant
import me.rerere.rikkahub.data.model.Avatar

/** 这条消息会不会被拆成多个小气泡 */
internal fun willSplitIntoBubbles(isUser: Boolean, assistant: Assistant?): Boolean {
    if (assistant == null) return false
    return if (isUser) assistant.effectiveUserSplitMode.isEnabled else assistant.bubbleSplitMode.isEnabled
}

/** 文本气泡该用哪个拆分模式 */
internal fun resolveSplitMode(isUser: Boolean, assistant: Assistant?): me.rerere.rikkahub.data.model.BubbleSplitMode {
    if (assistant == null) return me.rerere.rikkahub.data.model.BubbleSplitMode.NONE
    return if (isUser) assistant.effectiveUserSplitMode else assistant.bubbleSplitMode
}

/**
 * 外层那个固定侧边头像要不要藏起来。
 * 只要这条消息里有会自带头像的块，外层就必须让位，否则会出现两个。
 */
internal fun shouldHideSideAvatar(isUser: Boolean, assistant: Assistant?): Boolean {
    return willSplitIntoBubbles(isUser, assistant)
}

/**
 * 气泡内是否自带头像。
 * 只有开了拆分才由每个气泡自己画，否则返回 null 交给外层统一画。
 */
internal fun segmentAvatarFor(
    isUser: Boolean,
    assistant: Assistant?,
    model: Model?,
    userAvatar: Avatar,
    userNickname: String,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
): SegmentAvatarSpec? {
    val split = willSplitIntoBubbles(isUser, assistant)
    if (!split) return null
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

/** 图片/视频/音频/文档 旁边的头像，不受拆分开关影响 */
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
