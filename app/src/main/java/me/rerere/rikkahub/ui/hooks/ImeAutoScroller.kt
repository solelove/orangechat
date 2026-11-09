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
 * 键盘高度在弹出动画期间逐帧变化。逐帧都 scrollBy 会连滚几十帧导致卡顿；
 * 但完全只滚最后一次又有风险——一旦那次没触发，列表就永远不跟手。
 *
 * 折中方案：高度每变化 60px 以上才滚一次，动画期间最多滚几次，
 * 结束时再 debounce 一次补偿到最终位置。
 */
@OptIn(FlowPreview::class)
@Composable
fun ImeLazyListAutoScroller(
    lazyListState: LazyListState,
) {
    val ime = WindowInsets.ime
    val localDensity = LocalDensity.current
    var imeHeight by remember { mutableIntStateOf(0) }
    var lastScrolled by remember { mutableIntStateOf(0) }

    LaunchedEffect(Unit) {
        snapshotFlow { ime.getBottom(localDensity) }
            .distinctUntilChanged()
            .collect { keyboardHeight ->
                val delta = keyboardHeight - lastScrolled
                // 变化足够大就立刻跟一次，避免完全不跟手
                if (kotlin.math.abs(delta) >= 60) {
                    lazyListState.scrollBy(delta.toFloat())
                    lastScrolled = keyboardHeight
                }
                imeHeight = keyboardHeight
            }
    }

    // 动画结束后把差值补齐，保证最终位置精确
    LaunchedEffect(Unit) {
        snapshotFlow { ime.getBottom(localDensity) }
            .distinctUntilChanged()
            .debounce(120)
            .collect { keyboardHeight ->
                val delta = keyboardHeight - lastScrolled
                if (delta != 0) {
                    lazyListState.scrollBy(delta.toFloat())
                    lastScrolled = keyboardHeight
                }
                if (keyboardHeight == 0 && lazyListState.firstVisibleItemIndex <= 2) {
                    lazyListState.scrollToItem(0)
                }
            }
    }
}
