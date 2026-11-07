/*
 * 橘瓣 OrangeChat
 * 侧边头像：拆分气泡时不重复显示
 */

package me.rerere.rikkahub.ui.components.message

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import me.rerere.ai.core.MessageRole
import me.rerere.ai.provider.Model
import me.rerere.ai.ui.UIMessage
import me.rerere.rikkahub.data.model.Assistant
import me.rerere.rikkahub.data.model.Avatar
import me.rerere.rikkahub.ui.components.ui.AutoAIIcon
import me.rerere.rikkahub.ui.components.ui.UIAvatar
import me.rerere.rikkahub.ui.context.LocalDisplaySettings

/** 助手侧边头像：气泡被拆开时不再画（小气泡自带） */
@Composable
internal fun SideAvatarOrNothing(
    message: UIMessage,
    model: Model?,
    assistant: Assistant?,
    loading: Boolean,
) {
    val display = LocalDisplaySettings.current
    if (message.role != MessageRole.ASSISTANT) return
    if (!display.showModelIcon) return
    if (willSplitIntoBubbles(false, assistant) && display.showAssistantBubble) return

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

/** 用户侧边头像：气泡被拆开时不再画（小气泡自带） */
@Composable
internal fun SideUserAvatarOrNothing(
    message: UIMessage,
    avatar: Avatar,
    nickname: String,
    assistant: Assistant?,
) {
    val display = LocalDisplaySettings.current
    if (message.role != MessageRole.USER) return
    if (!display.showUserAvatar) return
    if (willSplitIntoBubbles(true, assistant)) return

    Box(modifier = Modifier.width(36.dp), contentAlignment = Alignment.TopCenter) {
        UIAvatar(
            name = nickname,
            modifier = Modifier.size(36.dp),
            value = avatar,
            loading = false,
        )
    }
}
