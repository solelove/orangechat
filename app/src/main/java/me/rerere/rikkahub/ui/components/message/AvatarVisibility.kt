/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.ui.components.message

import me.rerere.rikkahub.data.model.Assistant
import me.rerere.rikkahub.data.model.BubbleSplitMode

/** 该条消息是否会把气泡拆成多段 */
internal fun isSplitOn(role: String, assistant: Assistant?): Boolean {
    if (assistant == null) return false
    return if (role == "user") {
        assistant.effectiveUserSplitMode.isEnabled
    } else {
        assistant.bubbleSplitMode.isEnabled
    }
}

/** 拆成多段时，外层的侧边头像就不用画了，改由第一段小气泡自己带 */
internal fun shouldHideSideAvatar(
    isUser: Boolean,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    showAssistantBubble: Boolean,
    assistant: Assistant?,
): Boolean {
    if (assistant == null) return false
    return if (isUser) {
        showUserAvatar && assistant.effectiveUserSplitMode.isEnabled
    } else {
        showModelIcon && showAssistantBubble && assistant.bubbleSplitMode.isEnabled
    }
}
