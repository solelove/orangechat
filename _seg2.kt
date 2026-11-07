    annotations: List<UIMessageAnnotation>,
    loading: Boolean,
    onToolApproval: ((toolCallId: String, approved: Boolean, reason: String) -> Unit)? = null,
    onToolAnswer: ((toolCallId: String, answer: String) -> Unit)? = null,
    onUserMessageClick: (() -> Unit)? = null,
) {
    val context = LocalContext.current
    val contentColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
 
    val hapticFeedback = LocalHapticFeedback.current
    val displaySettings = LocalDisplaySettings.current
    val bubbleAlpha = 1f - displaySettings.chatBubbleTransparency / 100f
    val partsState by rememberUpdatedState(parts)

    // 气泡最大宽度：跟随内容，但不超过屏幕宽度的 72%
    val screenWidth = LocalConfiguration.current.screenWidthDp
    val maxBubbleWidth = (screenWidth * 0.72f).dp
 
    val handleClickCitation: (String) -> Unit = remember {
        handler@{ citationId ->
            partsState.forEach { part ->
                if (part is UIMessagePart.Tool && part.toolName == "search_web" && part.isExecuted) {
                    val outputText = part.output.filterIsInstance<UIMessagePart.Text>().joinToString("\n") { it.text }
                    val items =
                        runCatching { JsonInstant.parseToJsonElement(outputText).jsonObject["items"]?.jsonArray }.getOrNull()
                            ?: return@forEach
                    items.forEach { item ->
                        val id = item.jsonObject["id"]?.jsonPrimitive?.content ?: return@forEach
                        val url = item.jsonObject["url"]?.jsonPrimitive?.content ?: return@forEach
                        if (citationId == id) {
                            context.openUrl(url)
                            return@handler
                        }
                    }
                }
            }
        }
    }
    LaunchedEffect(displaySettings) {
        snapshotFlow { partsState }
            .debounce(50.milliseconds)
            .collect { parts ->
                if (parts.isNotEmpty() && loading && displaySettings.enableMessageGenerationHapticEffect) {
                    hapticFeedback.performHapticFeedback(HapticFeedbackType.KeyboardTap)
                }
            }
    }
 
    val groupedParts = remember(parts) { parts.groupMessageParts() }
    groupedParts.fastForEach { block ->
        when (block) {
            is MessagePartBlock.ThinkingBlock -> {
                if (block.steps.isNotEmpty()) {
                    val isReasoningOnlyBlock = block.steps.fastAll { it is ThinkingStep.ReasoningStep }
                    ChainOfThought(
                        modifier = Modifier.animateContentSize(),
                        steps = block.steps,
                        collapsedAdaptiveWidth = isReasoningOnlyBlock,
                    ) { step ->
                        when (step) {
                            is ThinkingStep.ReasoningStep -> {
                                key(step.reasoning.createdAt) {
                                    ChatMessageReasoningStep(
                                        reasoning = step.reasoning,
                                        model = model,
                                        assistant = assistant,
                                        collapsedAdaptiveWidth = isReasoningOnlyBlock,
                                    )
                                }
                            }
 
                            is ThinkingStep.ToolStep -> {
                                key(step.tool.toolCallId.ifBlank { step.hashCode().toString() }) {
                                    ChatMessageToolStep(
                                        tool = step.tool,
                                        loading = loading && !step.tool.isExecuted,
                                        allParts = parts,
                                        onToolApproval = onToolApproval,
                                        onToolAnswer = onToolAnswer,
                                    )
                                }
                            }
                        }
                    }
                }
            }
 
            is MessagePartBlock.ContentBlock -> key(block.index) {
                when (val part = block.part) {
                    is UIMessagePart.Text -> {
                        val displayText = remember(part.text) {
                            part.text.replace(Regex("\\[zip:[^\\]]+\\]", RegexOption.IGNORE_CASE), "")
                        }
                        val splitMode = assistant?.bubbleSplitMode ?: BubbleSplitMode.NONE
 
                        SelectionContainer {
                            Column {
                                if (role == MessageRole.USER) {
                                    SplitBubbleColumn(
                                        text = displayText,
                                        mode = assistant?.effectiveUserSplitMode ?: BubbleSplitMode.NONE,
                                        imagePath = displaySettings.userBubbleImagePath,
                                        cornerRadius = displaySettings.bubbleCornerRadius.dp,
                                        color = displaySettings.userBubbleColor?.let { it.toComposeColor() }
                                            ?: MaterialTheme.colorScheme.secondaryContainer,
                                        overlayEnabled = displaySettings.bubbleImageOverlayEnabled,
                                        bubbleAlpha = bubbleAlpha,
                                        maxWidth = maxBubbleWidth,
                                        alignment = Alignment.End,
                                        onClick = { onUserMessageClick?.invoke() },
                                        segmentAvatar = if (displaySettings.showUserAvatar)
                                            SegmentAvatarSpec.User(displaySettings.userAvatar, displaySettings.userNickname)
                                        else null,
                                    ) { segment ->
                                        MarkdownBlock(
                                            content = segment.replaceRegexes(
                                                assistant = assistant,
                                                scope = AssistantAffectScope.USER,
                                                visual = true,
                                            ),
                                            onClickCitation = handleClickCitation
                                        )
                                    }
                                } else {
                                    if (displaySettings.showAssistantBubble) {
                                        SplitBubbleColumn(
                                            text = displayText,
                                            mode = splitMode,
                                            imagePath = displaySettings.assistantBubbleImagePath,
                                            cornerRadius = displaySettings.bubbleCornerRadius.dp,
                                            color = displaySettings.assistantBubbleColor?.let { it.toComposeColor() }
                                                ?: MaterialTheme.colorScheme.surfaceContainerHigh,
                                            overlayEnabled = displaySettings.bubbleImageOverlayEnabled,
                                            bubbleAlpha = bubbleAlpha,
                                            maxWidth = maxBubbleWidth,
                                            alignment = Alignment.Start,
                                            segmentAvatar = when {
                                                !displaySettings.showModelIcon -> null
                                                assistant != null && assistant.useAssistantAvatar ->
                                                    SegmentAvatarSpec.AssistantAvatar(assistant)
                                                model != null -> SegmentAvatarSpec.Model(model.modelId)
                                                else -> null
                                            },
                                            avatarLoading = loading,
                                        ) { segment ->
                                            MarkdownBlock(
                                                content = segment.replaceRegexes(
                                                    assistant = assistant,
                                                    scope = AssistantAffectScope.ASSISTANT,
                                                    visual = true,
                                                ),
                                                onClickCitation = handleClickCitation,
                                            )
                                        }
                                    } else {
                                        MarkdownBlock(
                                            content = displayText.replaceRegexes(
                                                assistant = assistant,
                                                scope = AssistantAffectScope.ASSISTANT,
                                                visual = true,
                                            ),
                                            onClickCitation = handleClickCitation,
                                            modifier = Modifier.animateContentSize()
                                        )
                                    }
                                }
                            }
                        }
                    }