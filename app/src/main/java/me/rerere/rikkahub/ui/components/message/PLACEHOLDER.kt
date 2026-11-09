package me.rerere.rikkahub.ui.components.message

import me.rerere.rikkahub.data.model.Assistant
import me.rerere.rikkahub.data.model.BubbleSplitMode

// 头像归属判断现在全在 AvatarVisibility.kt，这里只保留 bubbleCarriesOwnAvatar 的兼容实现
// 不再使用：气泡内部不再根据自己的判断画头像，完全由 segmentAvatarFor 决定
