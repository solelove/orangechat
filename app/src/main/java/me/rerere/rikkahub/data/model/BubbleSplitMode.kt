/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * 气泡拆分模式
 *
 * NONE     一条消息一个气泡（默认）
 * LINE     按换行拆分
 * SENTENCE 按句子拆分，一句一个气泡
 */
@Serializable
enum class BubbleSplitMode {
    @SerialName("none")
    NONE,

    @SerialName("line")
    LINE,

    @SerialName("sentence")
    SENTENCE;

    val isEnabled: Boolean get() = this != NONE
}
