    val isUserMessage = message.role == MessageRole.USER

    // 拆分后每个小气泡自带头像，外层这个就不用再画了
    val hideSideAvatar = shouldHideSideAvatar(
        isUser = isUserMessage,
        showUserAvatar = settings.showUserAvatar,
        showModelIcon = settings.showModelIcon,
        showAssistantBubble = settings.showAssistantBubble,
        assistant = assistant,
    )

    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = if (isUserMessage) Arrangement.End else Arrangement.Start,
        verticalAlignment = Alignment.Top,
    ) {
        if (!isUserMessage && !message.parts.isEmptyUIMessage() && !hideSideAvatar) {
