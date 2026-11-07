                        val displayText = remember(part.text) {
                            part.text.replace(Regex("\\[zip:[^\\]]+\\]", RegexOption.IGNORE_CASE), "")
                        }
                        val userSplitMode = assistant?.effectiveUserSplitMode ?: BubbleSplitMode.NONE
                        val assistantSplitMode = assistant?.effectiveAssistantSplitMode ?: BubbleSplitMode.NONE
                        val userAvatarSpec: SegmentAvatarSpec? =
                            if (displaySettings.showUserAvatar)
                                SegmentAvatarSpec.User(displaySettings.userAvatar, displaySettings.userNickname)
                            else null
                        val assistantAvatarSpec: SegmentAvatarSpec? =
                            if (!displaySettings.showModelIcon) null
                            else if (assistant != null && assistant.useAssistantAvatar)
                                SegmentAvatarSpec.AssistantAvatar(assistant)
                            else model?.let { SegmentAvatarSpec.Model(it.modelId) }
 
                        SelectionContainer {
                            Column {
                                if (role == MessageRole.USER) {
                                    SplitBubbleColumn(
                                        text = displayText,
                                        mode = userSplitMode,
                                        imagePath = displaySettings.userBubbleImagePath,
                                        cornerRadius = displaySettings.bubbleCornerRadius.dp,
                                        color = displaySettings.userBubbleColor?.let { it.toComposeColor() }
                                            ?: MaterialTheme.colorScheme.secondaryContainer,
                                        overlayEnabled = displaySettings.bubbleImageOverlayEnabled,
                                        bubbleAlpha = bubbleAlpha,
                                        maxWidth = maxBubbleWidth,
                                        alignment = Alignment.End,
                                        onClick = { onUserMessageClick?.invoke() },
                                        segmentAvatar = userAvatarSpec,
                                        avatarLoading = false,
                                    ) { segment ->