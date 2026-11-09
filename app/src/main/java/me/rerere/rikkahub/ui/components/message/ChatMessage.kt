    // 这条消息里有没有非文本段（图片/视频/音频/文档/工具）
    val hasNonText = remember(parts) { parts.any { it !is UIMessagePart.Text } }

    // 文本气泡内的头像：开了拆分 或 混合消息(外层让位) 时自己带
    val textSegmentAvatar: SegmentAvatarSpec? = remember(role, assistant, model, displaySettings, hasNonText) {
        segmentAvatarFor(
            isUser = isUser,
            assistant = assistant,
            model = model,
            userAvatar = displaySettings.userAvatar,
            userNickname = displaySettings.userNickname,
            showUserAvatar = displaySettings.showUserAvatar,
            showModelIcon = displaySettings.showModelIcon,
            splitOrMixed = willSplitIntoBubbles(isUser, assistant) || hasNonText,
        )
    }
