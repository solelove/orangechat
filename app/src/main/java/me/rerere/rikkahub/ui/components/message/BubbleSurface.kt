/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.ui.components.message

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.util.fastForEachIndexed
import coil3.compose.AsyncImage
import me.rerere.rikkahub.data.model.Assistant
import me.rerere.rikkahub.data.model.Avatar
import me.rerere.rikkahub.data.model.BubbleSplitMode
import me.rerere.rikkahub.ui.components.ui.AutoAIIcon
import me.rerere.rikkahub.ui.components.ui.UIAvatar

/** 气泡拆分片段旁边的头像宽度 */
internal val SegmentAvatarWidth = 36.dp

/** 按模式切分气泡文本 */
fun splitByMode(text: String, mode: BubbleSplitMode): List<String> = when (mode) {
    BubbleSplitMode.NONE -> listOf(text)
    BubbleSplitMode.LINE -> text.split("\n").filter { it.isNotBlank() }.ifEmpty { listOf(text) }
    BubbleSplitMode.SENTENCE -> splitIntoSentences(text)
}

/** 按中英文句末标点切句，保留标点 */
private fun splitIntoSentences(text: String): List<String> {
    val result = mutableListOf<String>()
    val buffer = StringBuilder()
    text.forEach { ch ->
        buffer.append(ch)
        if (ch == '。' || ch == '！' || ch == '？' || ch == '!' || ch == '?' ||
            (ch == '.' && (buffer.length < 2 || buffer[buffer.length - 2] != '.'))
        ) {
            val piece = buffer.toString().trim()
            if (piece.isNotEmpty()) result.add(piece)
            buffer.setLength(0)
        }
    }
    val rest = buffer.toString().trim()
    if (rest.isNotEmpty()) result.add(rest)
    return result.ifEmpty { listOf(text) }
}

/** 拆分后每个气泡要显示的头像；为 null 表示不显示 */
sealed interface SegmentAvatarSpec {
    data class User(val avatar: Avatar, val nickname: String) : SegmentAvatarSpec
    data class AssistantAvatar(val assistant: Assistant) : SegmentAvatarSpec
    data class Model(val modelId: String) : SegmentAvatarSpec
}

@Composable
internal fun SegmentAvatarView(spec: SegmentAvatarSpec, loading: Boolean) {
    Box(modifier = Modifier.width(SegmentAvatarWidth), contentAlignment = Alignment.TopCenter) {
        when (spec) {
            is SegmentAvatarSpec.User -> UIAvatar(
                name = spec.nickname,
                modifier = Modifier.size(SegmentAvatarWidth),
                value = spec.avatar,
                loading = false,
            )

            is SegmentAvatarSpec.AssistantAvatar -> UIAvatar(
                name = spec.assistant.name,
                modifier = Modifier.size(SegmentAvatarWidth),
                value = spec.assistant.avatar,
                loading = loading,
            )

            is SegmentAvatarSpec.Model -> AutoAIIcon(
                name = spec.modelId,
                modifier = Modifier.size(SegmentAvatarWidth),
                loading = loading,
            )
        }
    }
}

/**
 * 按模式渲染一个气泡组。
 *
 * 不拆分时这里完全不画头像，交给外层 ChatMessage 画那一个；
 * 拆分时每段自己带一个，外层因为见下 hideSideAvatar 为 true 而让位。
 * 两种情况下每条消息都只有一个头像。
 */
@Composable
fun SplitBubbleColumn(
    text: String,
    mode: BubbleSplitMode,
    imagePath: String,
    cornerRadius: Dp,
    color: Color,
    overlayEnabled: Boolean,
    bubbleAlpha: Float,
    maxWidth: Dp,
    alignment: Alignment.Horizontal,
    onClick: (() -> Unit)? = null,
    segmentAvatar: SegmentAvatarSpec? = null,
    avatarLoading: Boolean = false,
    content: @Composable (String) -> Unit,
) {
    if (!mode.isEnabled) {
        BubbleSurface(
            imagePath = imagePath,
            cornerRadius = cornerRadius,
            color = color,
            overlayEnabled = overlayEnabled,
            bubbleAlpha = bubbleAlpha,
            maxWidth = maxWidth,
            animate = true,
            onClick = onClick,
        ) {
            content(text)
        }
        return
    }

    val segments = remember(text, mode) { splitByMode(text, mode) }
    val isRightSide = alignment == Alignment.End
    val avatarSpace = if (segmentAvatar != null) SegmentAvatarWidth + 8.dp else 0.dp
    val segmentMaxWidth = (maxWidth - avatarSpace).coerceAtLeast(120.dp)

    Column(
        verticalArrangement = Arrangement.spacedBy(4.dp),
        horizontalAlignment = alignment,
        modifier = Modifier.fillMaxWidth(),
    ) {
        segments.fastForEachIndexed { _, segment ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.Top,
                horizontalArrangement = if (isRightSide) Arrangement.End else Arrangement.Start,
            ) {
                if (segmentAvatar != null && !isRightSide) {
                    SegmentAvatarView(segmentAvatar, avatarLoading)
                    Spacer(modifier = Modifier.width(8.dp))
                }
                BubbleSurface(
                    imagePath = imagePath,
                    cornerRadius = cornerRadius,
                    color = color,
                    overlayEnabled = overlayEnabled,
                    bubbleAlpha = bubbleAlpha,
                    maxWidth = segmentMaxWidth,
                    onClick = onClick,
                ) {
                    content(segment)
                }
                if (segmentAvatar != null && isRightSide) {
                    Spacer(modifier = Modifier.width(8.dp))
                    SegmentAvatarView(segmentAvatar, avatarLoading)
                }
            }
        }
    }
}

/** 气泡外壳：宽度跟随内容，最大不超过 [maxWidth] */
@Composable
fun BubbleSurface(
    imagePath: String,
    cornerRadius: Dp,
    color: Color,
    overlayEnabled: Boolean,
    bubbleAlpha: Float,
    maxWidth: Dp,
    onClick: (() -> Unit)? = null,
    animate: Boolean = false,
    content: @Composable () -> Unit,
) {
    // 文件存在性检查会走磁盘，缓存起来避免每次重组都查
    val hasImage = remember(imagePath) {
        imagePath.isNotBlank() && runCatching { java.io.File(imagePath).exists() }.getOrDefault(false)
    }
    if (hasImage) {
        Box(
            modifier = Modifier
                .then(if (animate) Modifier.animateContentSize() else Modifier)
                .widthIn(max = maxWidth)
                .clip(RoundedCornerShape(cornerRadius))
                .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
        ) {
            AsyncImage(
                model = imagePath,
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.matchParentSize()
            )
            if (overlayEnabled) {
                Box(
                    modifier = Modifier
                        .matchParentSize()
                        .background(color.copy(alpha = bubbleAlpha))
                )
            }
            Column(modifier = Modifier.padding(8.dp)) { content() }
        }
    } else {
        Surface(
            modifier = Modifier
                .animateContentSize()
                .widthIn(max = maxWidth),
            shape = RoundedCornerShape(cornerRadius),
            color = color.copy(alpha = bubbleAlpha),
            onClick = onClick ?: {},
        ) {
            Column(modifier = Modifier.padding(8.dp)) { content() }
        }
    }
}
