package me.rerere.rikkahub.ui.components.message

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import me.rerere.rikkahub.ui.components.ui.AutoAIIcon
import me.rerere.rikkahub.ui.components.ui.UIAvatar

/**
 * 非文本段（图片/视频/文档/音频）外框。
 *
 * 头像不在这里画。一条消息的头像统一由 ChatMessage 外层画一次，
 * 否则图片行和文字气泡会各自带一个，同一条消息后面出现两个头像。
 */
@Composable
internal fun PartRow(
    isUser: Boolean,
    content: @Composable () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top,
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        content()
    }
}

@Composable
internal fun PartAvatarViewPlaceholder() {
    // 保留空实现，避免旧引用编译失败
    Box(modifier = Modifier.size(0.dp)) {}
}
