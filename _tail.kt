@Composable
private fun ChatMessageSideAvatar(
    message: UIMessage,
    model: Model?,
    assistant: Assistant?,
    loading: Boolean,
) {
    SideAvatarOrNothing(
        message = message,
        model = model,
        assistant = assistant,
        loading = loading,
    )
}

@Composable
private fun ChatMessageSideUserAvatar(
    message: UIMessage,
    avatar: Avatar,
    nickname: String,
) {
    SideUserAvatarOrNothing(
        message = message,
        avatar = avatar,
        nickname = nickname,
        assistant = null,
    )
}
