/*
 * 橘瓣 OrangeChat
 * 拆分气泡时外层头像隐藏逻辑
 */

package me.rerere.rikkahub.ui.components.message

import me.rerere.rikkahub.data.model.Assistant

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
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    showAssistantBubble: Boolean,
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
