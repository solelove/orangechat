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
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.distinctUntilChanged

/**
 * 键盘弹出时把聊天列表顶上去。
 *
 * 键盘高度在弹出动画期间逐帧变化，旧实现每帧都会进 collect 并 delay，
 * delay 结束后照样 scrollBy，等于一次弹键盘滚动十几二十次，布局反复重算，
 * 表现为"弹键盘/收键盘时卡一下"。
 *
 * 现在用 collectLatest：新高度一来就取消上一次还没走完的 delay，
 * 只有高度真正稳定 150ms 后才滚一次。
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
            .collectLatest { keyboardHeight ->
                // 键盘动画期间高度每帧都变，上一次的等待会被取消
                delay(150)
                if (keyboardHeight > 0) {
                    val delta = keyboardHeight - imeHeight
                    if (delta != 0) {
                        lazyListState.scrollBy(delta.toFloat())
                        imeHeight = keyboardHeight
                    }
                } else {
                    imeHeight = 0
                }
            }
    }
}
