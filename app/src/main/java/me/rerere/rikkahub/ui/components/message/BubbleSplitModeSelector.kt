/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.ui.components.message

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import me.rerere.rikkahub.data.model.BubbleSplitMode

/**
 * 气泡拆分模式选择器：不拆 / 按换行 / 按句子
 *
 * 用分段按钮的形式，避免两个独立开关互相打架。
 */
@Composable
fun BubbleSplitModeSelector(
    selected: BubbleSplitMode,
    onSelect: (BubbleSplitMode) -> Unit,
    modifier: Modifier = Modifier,
) {
    val options = listOf(
        BubbleSplitMode.NONE to "不拆",
        BubbleSplitMode.LINE to "按换行",
        BubbleSplitMode.SENTENCE to "按句子",
    )

    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        options.forEach { (mode, label) ->
            val isSelected = mode == selected
            Row(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(9.dp))
                    .background(
                        if (isSelected) MaterialTheme.colorScheme.secondaryContainer
                        else androidx.compose.ui.graphics.Color.Transparent
                    )
                    .clickable { onSelect(mode) }
                    .padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = label,
                    style = MaterialTheme.typography.labelLarge,
                    color = if (isSelected) MaterialTheme.colorScheme.onSecondaryContainer
                    else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
