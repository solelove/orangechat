# -*- coding: utf-8 -*-
"""把 ChatMessage.kt 改成微信式布局：头像和气泡同一行。"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessage.kt")
src = P.read_text(encoding="utf-8")

OLD_HEAD = '''    Column(
        modifier = modifier.fillMaxWidth(),
        horizontalAlignment = if (message.role == MessageRole.USER) Alignment.End else Alignment.Start,
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        if (!message.parts.isEmptyUIMessage()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.End),
            ) {
                ChatMessageAssistantAvatar(
                    message = message,
                    model = model,
                    assistant = assistant,
                    loading = loading,
                    modifier = Modifier.weight(1f)
                )
                ChatMessageUserAvatar(
                    message = message,
                    avatar = settings.userAvatar,
                    nickname = settings.userNickname,
                    modifier = Modifier.weight(1f)
                )
            }
        }
'''

NEW_HEAD = '''    val isUserMessage = message.role == MessageRole.USER
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = if (isUserMessage) Arrangement.End else Arrangement.Start,
        verticalAlignment = Alignment.Top,
    ) {
        if (!isUserMessage && !message.parts.isEmptyUIMessage()) {
            ChatMessageSideAvatar(
                message = message,
                model = model,
                assistant = assistant,
                loading = loading,
            )
            Spacer(modifier = Modifier.width(8.dp))
        }
        Column(
            modifier = Modifier.weight(1f, fill = false),
            horizontalAlignment = if (isUserMessage) Alignment.End else Alignment.Start,
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
'''

OLD_TAIL = '''        ProvideTextStyle(textStyle) {
            ChatMessageNerdLine(message = message)
        }
    }
    if (showActionsSheet) {
'''

NEW_TAIL = '''        ProvideTextStyle(textStyle) {
            ChatMessageNerdLine(message = message)
        }
    }
        if (isUserMessage && !message.parts.isEmptyUIMessage()) {
            Spacer(modifier = Modifier.width(8.dp))
            ChatMessageSideUserAvatar(
                message = message,
                avatar = settings.userAvatar,
                nickname = settings.userNickname,
            )
        }
    }
    if (showActionsSheet) {
'''

OLD_IMPORT = 'import me.rerere.rikkahub.ui.components.ui.Favicon\n'

NEW_IMPORT = (
    'import me.rerere.rikkahub.ui.components.ui.Favicon\n'
    'import me.rerere.rikkahub.ui.components.ui.AutoAIIcon\n'
    'import me.rerere.rikkahub.ui.components.ui.UIAvatar\n'
    'import me.rerere.rikkahub.data.model.Avatar\n'
)

EXTRA = '''
@Composable
private fun ChatMessageSideAvatar(
    message: UIMessage,
    model: Model?,
    assistant: Assistant?,
    loading: Boolean,
) {
    val display = LocalDisplaySettings.current
    if (message.role == MessageRole.ASSISTANT && display.showModelIcon) {
        val useAssistantAvatar = assistant?.useAssistantAvatar == true
        Box(modifier = Modifier.width(36.dp), contentAlignment = Alignment.TopCenter) {
            if (useAssistantAvatar && assistant != null) {
                UIAvatar(
                    name = assistant.name,
                    modifier = Modifier.size(36.dp),
                    value = assistant.avatar,
                    loading = loading,
                )
            } else if (model != null) {
                AutoAIIcon(
                    name = model.modelId,
                    modifier = Modifier.size(36.dp),
                    loading = loading,
                )
            }
        }
    }
}

@Composable
private fun ChatMessageSideUserAvatar(
    message: UIMessage,
    avatar: Avatar,
    nickname: String,
) {
    val display = LocalDisplaySettings.current
    if (message.role == MessageRole.USER && display.showUserAvatar) {
        Box(modifier = Modifier.width(36.dp), contentAlignment = Alignment.TopCenter) {
            UIAvatar(
                name = nickname,
                modifier = Modifier.size(36.dp),
                value = avatar,
                loading = false,
            )
        }
    }
}
'''


def sub(text: str, old: str, new: str, tag: str) -> str:
    count = text.count(old)
    if count != 1:
        print("[patch] locate failed: %s hits=%d" % (tag, count))
        sys.exit(1)
    print("[patch] ok %s" % tag)
    return text.replace(old, new)


src = sub(src, OLD_HEAD, NEW_HEAD, "head")
src = sub(src, OLD_TAIL, NEW_TAIL, "tail")
src = sub(src, OLD_IMPORT, NEW_IMPORT, "import")
src = src.rstrip() + "\n" + EXTRA
P.write_text(src, encoding="utf-8")
print("[patch] done")
