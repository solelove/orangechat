/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.ui.hooks

import androidx.compose.foundation.gestures.scrollBy
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.platform.LocalDensity
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.distinctUntilChanged

/**
 * 键盘弹出时把聊天列表顶上去。
 *
 * 键盘高度在弹出动画期间会逐帧变化，早期实现每帧都 scrollBy 一次，
 * 列表跟着连滚几十帧，布局反复重算，表现为"弹键盘时卡一下"。
 * 现在改成：等高度稳定（连续 80ms 不再变化）后只滚一次。
 */
@Composable
fun ImeLazyListAutoScroller(
    lazyListState: LazyListState,
) {
    val ime = WindowInsets.ime
    val localDensity = LocalDensity.current
    var imeHeight by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) {
        snapshotFlow { ime.getBottom(localDensity) }
            .distinctUntilChanged()
            .collect { keyboardHeight ->
                // 等键盘动画结束：高度连续不变 80ms 后才认为稳定
                delay(80)
                if (keyboardHeight > 0 && keyboardHeight != imeHeight) {
                    lazyListState.scrollBy((keyboardHeight - imeHeight).toFloat())
                    imeHeight = keyboardHeight
                } else if (keyboardHeight == 0) {
                    imeHeight = 0
                }
            }
    }
}
