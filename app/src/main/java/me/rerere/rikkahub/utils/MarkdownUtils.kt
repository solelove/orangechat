/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.utils
 
/**
 * 移除字符串中的Markdown格式
 * @return 移除Markdown格式后的纯文本
 */
fun String.stripMarkdown(): String {
    return this
        // 移除代码块 (```...``` 和 `...`)
        .replace(Regex("```[\\s\\S]*?```|`[^`]*?`"), "")
        // 移除图片和链接，但保留其文本内容
        .replace(Regex("!?\\[([^\\]]+)\\]\\([^\\)]*\\)"), "$1")
        // 移除加粗和斜体 (先处理两个星号的)
        .replace(Regex("\\*\\*([^*]+?)\\*\\*"), "$1")
        .replace(Regex("\\*([^*]+?)\\*"), "$1")
        // 移除下划线
        .replace(Regex("__([^_]+?)__"), "$1")
        .replace(Regex("_([^_]+?)_"), "$1")
        // 移除删除线
        .replace(Regex("~~([^~]+?)~~"), "$1")
        // 移除标题标记 (多行模式)
        .replace(Regex("(?m)^#+\\s*"), "")
        // 移除列表标记 (多行模式)
        .replace(Regex("(?m)^\\s*[-*+]\\s+"), "")
        .replace(Regex("(?m)^\\s*\\d+\\.\\s+"), "")
        // 移除引用标记 (多行模式)
        .replace(Regex("(?m)^>\\s*"), "")
        // 移除水平分割线
        .replace(Regex("(?m)^(\\s*[-*_]){3,}\\s*$"), "")
        // 将多个换行符压缩，以保留段落
        .replace(Regex("\\n{3,}"), "\\n\\n")
        .trim()
}
 
fun String.extractThinkingTitle(): String? {
    // 按行分割文本
    val lines = this.lines()
 
    // 从后往前查找最后一个符合条件的加粗文本行
    for (i in lines.indices.reversed()) {
        val line = lines[i].trim()
 
        // 检查是否为加粗格式且独占一整行
        val boldPattern = Regex("^\\*\\*(.+?)\\*\\*$")
        val match = boldPattern.find(line)
 
        if (match != null) {
            // 返回加粗标记内的文本内容
            return match.groupValues[1].trim().takeUnless { it.isBlank() }
        }
    }
 
    return null
}
 
// ============================================================
// 分句气泡: 把一条回复拆成若干个气泡片段
// ============================================================
 
/**
 * 围栏代码块 (```...```)，内部的换行必须原样保留，不能被当作气泡边界。
 * 复用与 MarkdownNew.kt / stripMarkdown 相同的匹配方式，保持项目内一致的约定。
 */
private val FENCED_CODE_BLOCK_REGEX = Regex("```[\\s\\S]*?```")
 
/**
 * 找出文本中「不可在其内部拆分气泡」的字符区间：
 * 1. 围栏代码块 (```...```) —— 内部换行是代码的一部分，拆开代码就碎了
 * 2. Markdown 表格 —— 连续 2 行及以上、每行都形如 "|...|" 的区块，拆开表格就散架了
 */
private fun findProtectedRanges(text: String): List<IntRange> {
    val ranges = mutableListOf<IntRange>()
 
    // 1. 围栏代码块
    FENCED_CODE_BLOCK_REGEX.findAll(text).forEach { ranges.add(it.range) }
 
    // 2. Markdown 表格块
    fun isTableRow(line: String): Boolean {
        val trimmed = line.trim()
        return trimmed.length > 1 && trimmed.startsWith("|") && trimmed.endsWith("|")
    }
 
    val lines = text.lines()
    var lineStartOffset = 0
    var tableStartLineIndex = -1
    var tableStartOffset = 0
 
    lines.forEachIndexed { index, line ->
        if (isTableRow(line)) {
            if (tableStartLineIndex == -1) {
                tableStartLineIndex = index
                tableStartOffset = lineStartOffset
            }
        } else {
            if (tableStartLineIndex != -1 && index - tableStartLineIndex >= 2) {
                // 表格至少需要 2 行 (表头 + 分隔行)，才当作一张完整表格保护起来
                ranges.add(tableStartOffset until (lineStartOffset - 1).coerceAtLeast(tableStartOffset))
            }
            tableStartLineIndex = -1
        }
        lineStartOffset += line.length + 1 // +1 计入被 lines() 消费掉的那个 '\n'
    }
    // 文本结尾仍处于表格中 (没有后续非表格行来"关闭"它)
    if (tableStartLineIndex != -1 && lines.size - tableStartLineIndex >= 2) {
        ranges.add(tableStartOffset until text.length)
    }
 
    return ranges
}
 
/**
 * 按模型自己写的换行符 (\n) 把一条助手回复拆分成多个"气泡"片段。
 */
fun String.splitIntoBubbleSegments(): List<String> {
    if (isBlank()) return listOf(this)
 
    val protectedRanges = findProtectedRanges(this)
    fun isProtectedIndex(index: Int) = protectedRanges.any { index in it }
 
    val segments = mutableListOf<String>()
    val current = StringBuilder()
    for (index in indices) {
        val ch = this[index]
        if (ch == '\n' && !isProtectedIndex(index)) {
            segments.add(current.toString())
            current.clear()
        } else {
            current.append(ch)
        }
    }
    segments.add(current.toString())
 
    val result = segments
        .map { it.trim('\r').trim() }
        .filter { it.isNotBlank() }
 
    return result.ifEmpty { listOf(this.trim()) }
}

// ============================================================
// 按句子拆分: 一句一个气泡
// ============================================================

/** 句子结束符。英文标点后面必须跟空白或结尾，避免把 3.14 / a.b 拆开。 */
private val SENTENCE_END_CHARS = charArrayOf('。', '！', '？', '!', '?', '…', '~', '～')

/**
 * 把一段文本按句子拆成多个气泡片段。
 *
 * 规则：
 * - 中文句号/问号/感叹号/省略号/波浪号后面直接断句
 * - 英文 .!? 后面必须跟空白、换行或文本结尾才断（防止拆开小数与网址）
 * - 紧跟在结束符后的引号、括号、逗号等收尾符号会吞进同一句
 * - 代码块与 Markdown 表格内部的换行/标点不参与断句
 * - 换行本身也作为断句点
 * - 过短的碎片（少于 3 个字符且不含结束符）会合并到前一句
 */
fun String.splitIntoSentenceBubbles(): List<String> {
    if (isBlank()) return listOf(this)

    val protectedRanges = findProtectedRanges(this)
    fun isProtectedIndex(index: Int) = protectedRanges.any { index in it }

    // 需要吞进上一句的收尾符号
    val trailingChars = charArrayOf(
        '"', '\'', '”', '’', '）', ')', '】', ']', '》', '」', '』',
        '，', ',', '、', '；', ';', '：', ':'
    )

    val segments = mutableListOf<String>()
    val current = StringBuilder()
    var i = 0
    val n = length

    while (i < n) {
        val ch = this[i]
        current.append(ch)

        val isEnd = when {
            isProtectedIndex(i) -> false
            ch == '\n' -> true
            ch in SENTENCE_END_CHARS -> true
            ch == '.' -> {
                // 英文句点: 后面必须是空白或结尾
                val next = getOrNull(i + 1)
                next == null || next.isWhitespace()
            }
            else -> false
        }

        if (isEnd) {
            i++
            // 吞掉紧跟的收尾符号（保护区内不动）
            while (i < n && this[i] in trailingChars && !isProtectedIndex(i)) {
                current.append(this[i])
                i++
            }
            segments.add(current.toString())
            current.clear()
            continue
        }
        i++
    }
    if (current.isNotEmpty()) segments.add(current.toString())

    val cleaned = segments
        .map { it.trim('\r').trim() }
        .filter { it.isNotBlank() }

    if (cleaned.isEmpty()) return listOf(this.trim())

    // 合并过短的碎片到前一句，避免出现只有一个标点的气泡
    val merged = mutableListOf<String>()
    cleaned.forEach { seg ->
        val last = merged.lastOrNull()
        val tooShort = seg.length <= 2 && seg.none { it in SENTENCE_END_CHARS || it == '.' }
        if (last != null && tooShort) {
            merged[merged.lastIndex] = last + seg
        } else {
            merged.add(seg)
        }
    }

    return merged.ifEmpty { listOf(this.trim()) }
}
