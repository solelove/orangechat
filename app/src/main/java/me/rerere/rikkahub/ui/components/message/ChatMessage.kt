    // 没开拆分时，外层统一画那唯一一个头像（纯文本、文字+图片都一样）；开了拆分交给各段
    val sideAvatarVisible = remember(message.parts, assistant) {
        !message.parts.isEmptyUIMessage() &&
            !shouldHideSideAvatar(isUserMessage, assistant)
    }
