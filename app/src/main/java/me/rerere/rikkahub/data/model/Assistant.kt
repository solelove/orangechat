    // 气泡拆分模式：none 不拆 / line 按换行 / sentence 按句子（用户与助手共用）
    val bubbleSplitMode: BubbleSplitMode = BubbleSplitMode.NONE,
) {
    /** 兼容旧字段：按换行拆分时为 true */
    val splitBubbleByLine: Boolean
        get() = bubbleSplitMode == BubbleSplitMode.LINE
}
