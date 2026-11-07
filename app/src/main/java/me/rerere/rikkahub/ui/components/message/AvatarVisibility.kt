/* 处理气泡拆分的头像占用 */
package me.rerere.rikkahub.ui.components.message

import me.rerere.rikkahub.data.model.Assistant

/** 拆分成多个气泡时，外层的侧边头像要隐藏，改由第一段气泡自己带 */
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
