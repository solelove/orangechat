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
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.distinctUntilChanged

/**
 * 键盘弹出时把聊天列表顶上去。
 *
 * 键盘高度在弹出动画期间逐帧变化，旧实现每帧都 scrollBy 一次，
 * 列表跟着连滚几十帧，布局反复重算，表现为弹键盘时卡一下。
 *
 * 现在用 debounce：等高度连续 120ms 不再变化后，才用一个最终值滚一次。
 * 注意不能用 collectLatest 里 delay 的写法，那样最后一次也会被
 * 后续事件取消掉，结果就完全不滚了。
 */
@OptIn(FlowPreview::class)
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
            .debounce(120)
            .collect { keyboardHeight ->
                if (keyboardHeight > 0) {
                    val delta = keyboardHeight - imeHeight
                    if (delta != 0) {
                        lazyListState.scrollBy(delta.toFloat())
                        imeHeight = keyboardHeight
                    }
                } else {
                    imeHeight = 0
                }
                // 键盘收起后回到最新一条，跟原生行为一致
                if (lazyListState.firstVisibleItemIndex <= 2) {
                    lazyListState.scrollToItem(0)
                }
            }
    }
}
