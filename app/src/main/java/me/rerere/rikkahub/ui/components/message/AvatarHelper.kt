/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.ui.components.message

import me.rerere.rikkahub.data.model.Assistant

/** 拆分气泡时外层头像隐藏判断（见 AvatarVisibility.kt） */

/** 拆分前应把外层头像藏起来，否则会和小气泡里的头像重复 */
internal fun hideOuterAvatarFor(
    isUserMessage: Boolean,
    showUserAvatar: Boolean,
    showModelIcon: Boolean,
    showAssistantBubble: Boolean,
    assistant: Assistant?,
): Boolean = shouldHideSideAvatar(
    isUser = isUserMessage,
    showUserAvatar = showUserAvatar,
    showModelIcon = showModelIcon,
    showAssistantBubble = showAssistantBubble,
    assistant = assistant,
)
