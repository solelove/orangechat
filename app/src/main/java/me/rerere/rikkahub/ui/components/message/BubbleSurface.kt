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
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.key
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
import me.rerere.rikkahub.data.model.BubbleSplitMode
import me.rerere.rikkahub.utils.splitIntoBubbleSegments
import me.rerere.rikkahub.utils.splitIntoSentenceBubbles

/** 按模式切分气泡文本 */
fun splitByMode(text: String, mode: BubbleSplitMode): List<String> = when (mode) {
    BubbleSplitMode.NONE -> listOf(text)
    BubbleSplitMode.LINE -> text.splitIntoBubbleSegments()
    BubbleSplitMode.SENTENCE -> text.splitIntoSentenceBubbles()
}

/**
 * 按模式渲染一个气泡组。
 *
 * - 模式为 NONE 时直接渲染一个整体气泡（保持原有行为）
 * - 模式为 LINE / SENTENCE 时按行或按句拆成多个小气泡，一句一框
 * - 气泡宽度跟随内容，最宽不超过 [maxWidth]
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
            onClick = onClick,
        ) {
            content(text)
        }
        return
    }

    val segments = remember(text, mode) { splitByMode(text, mode) }
    Column(
        verticalArrangement = Arrangement.spacedBy(4.dp),
        horizontalAlignment = alignment,
    ) {
        segments.fastForEachIndexed { index, segment ->
            key(index) {
                BubbleSurface(
                    imagePath = imagePath,
                    cornerRadius = cornerRadius,
                    color = color,
                    overlayEnabled = overlayEnabled,
                    bubbleAlpha = bubbleAlpha,
                    maxWidth = maxWidth,
                    onClick = onClick,
                ) {
                    content(segment)
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
    content: @Composable () -> Unit,
) {
    val hasImage = imagePath.isNotBlank() && java.io.File(imagePath).exists()
    if (hasImage) {
        Box(
            modifier = Modifier
                .animateContentSize()
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
