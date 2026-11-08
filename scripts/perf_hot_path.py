# -*- coding: utf-8 -*-
"""热路径优化：字体 / 正则 / 时间条 / 模型查找 / 气泡动画"""

import pathlib
import re
import sys

BASE = pathlib.Path("app/src/main/java/me/rerere/rikkahub")

MSG = BASE / "ui/components/message/ChatMessage.kt"
BUBBLE = BASE / "ui/components/message/BubbleSurface.kt"
LIST = BASE / "ui/pages/chat/ChatList.kt"


def read(p):
    return p.read_text(encoding="utf-8")


def write(p, s):
    p.write_text(s, encoding="utf-8")
    print("patched:", p)


def patch_chat_message():
    s = read(MSG)
    changed = False

    old_font = """    val textStyle = LocalTextStyle.current.copy(
        fontSize = LocalTextStyle.current.fontSize * settings.fontSizeRatio,
        color = settings.chatTextColor?.let { it.toComposeColor() } ?: Color.Unspecified,
        lineHeight = LocalTextStyle.current.lineHeight * settings.fontSizeRatio,
        fontFamily = when (settings.chatFontFamily) {
            ChatFontFamily.DEFAULT -> FontFamily.Default
            ChatFontFamily.SERIF -> FontFamily.Serif
            ChatFontFamily.MONOSPACE -> FontFamily.Monospace
            ChatFontFamily.CUSTOM -> {
                val fontPath = settings.customFontPath
                if (fontPath.isNotBlank() && java.io.File(fontPath).exists()) {
                    FontFamily(Font(java.io.File(fontPath)))
                } else {
                    FontFamily.Default
                }
            }
        }
    )"""

    new_font = """    val fontFamily = remember(settings.chatFontFamily, settings.customFontPath) {
        when (settings.chatFontFamily) {
            ChatFontFamily.DEFAULT -> FontFamily.Default
            ChatFontFamily.SERIF -> FontFamily.Serif
            ChatFontFamily.MONOSPACE -> FontFamily.Monospace
            ChatFontFamily.CUSTOM -> {
                val fontPath = settings.customFontPath
                if (fontPath.isNotBlank()) {
                    runCatching {
                        if (java.io.File(fontPath).exists()) {
                            FontFamily(Font(java.io.File(fontPath)))
                        } else {
                            FontFamily.Default
                        }
                    }.getOrDefault(FontFamily.Default)
                } else {
                    FontFamily.Default
                }
            }
        }
    }
    val baseTextStyle = LocalTextStyle.current
    val chatTextColor = remember(settings.chatTextColor) {
        settings.chatTextColor?.let { it.toComposeColor() } ?: Color.Unspecified
    }
    val textStyle = remember(baseTextStyle, settings.fontSizeRatio, chatTextColor, fontFamily) {
        baseTextStyle.copy(
            fontSize = baseTextStyle.fontSize * settings.fontSizeRatio,
            color = chatTextColor,
            lineHeight = baseTextStyle.lineHeight * settings.fontSizeRatio,
            fontFamily = fontFamily,
        )
    }"""

    if old_font in s:
        s = s.replace(old_font, new_font)
        changed = True
        print("  font -> remember")

    if "private val ZipMarkRegex = Regex(" not in s:
        anchor = "@Composable\nfun ChatMessage("
        const = 'private val ZipMarkRegex = Regex("\\\\[zip:[^\\\\]]+\\\\]", RegexOption.IGNORE_CASE)\n\n'
        if anchor in s:
            s = s.replace(anchor, const + anchor, 1)
            changed = True
            print("  zip regex -> const")

    s2 = re.sub(
        r'part\.text\.replace\(\s*Regex\("\\\\\[zip:\[\^\\\\\]\]\+\\\\\]",\s*RegexOption\.IGNORE_CASE\),\s*""\s*\)',
        'part.text.replace(ZipMarkRegex, "")',
        s,
    )
    if s2 != s:
        s = s2
        changed = True
        print("  zip regex call -> const")

    old_max = """    val screenWidth = LocalConfiguration.current.screenWidthDp
    val maxBubbleWidth = (screenWidth * 0.72f).dp"""
    new_max = """    val screenWidth = LocalConfiguration.current.screenWidthDp
    val maxBubbleWidth = remember(screenWidth) { (screenWidth * 0.72f).dp }"""
    if old_max in s:
        s = s.replace(old_max, new_max)
        changed = True
        print("  bubble max width -> remember")

    if changed:
        write(MSG, s)
    else:
        print("ChatMessage.kt: nothing matched")


def patch_bubble_surface():
    s = read(BUBBLE)
    orig = s
    changed = False

    old_sig = """    maxWidth: Dp,
    onClick: (() -> Unit)? = null,
    content: @Composable () -> Unit,
) {"""
    new_sig = """    maxWidth: Dp,
    onClick: (() -> Unit)? = null,
    animate: Boolean = false,
    content: @Composable () -> Unit,
) {"""
    if old_sig in s:
        s = s.replace(old_sig, new_sig, 1)
        changed = True
        print("  BubbleSurface animate param")

    s = s.replace(
        """            modifier = Modifier
                .animateContentSize()
                .widthIn(max = maxWidth)
                .clip(RoundedCornerShape(cornerRadius))""",
        """            modifier = Modifier
                .widthIn(max = maxWidth)
                .clip(RoundedCornerShape(cornerRadius))""",
    )

    if """            modifier = Modifier
                .then(if (animate) Modifier.animateContentSize() else Modifier)
                .widthIn(max = maxWidth),""" not in s:
        s = s.replace(
            """            modifier = Modifier
                .animateContentSize()
                .widthIn(max = maxWidth),""",
            """            modifier = Modifier
                .then(if (animate) Modifier.animateContentSize() else Modifier)
                .widthIn(max = maxWidth),""",
            1,
        )

    old_single = """        BubbleSurface(
            imagePath = imagePath,
            cornerRadius = cornerRadius,
            color = color,
            overlayEnabled = overlayEnabled,
            bubbleAlpha = bubbleAlpha,
            maxWidth = maxWidth,
            onClick = onClick,
        ) {"""
    new_single = """        BubbleSurface(
            imagePath = imagePath,
            cornerRadius = cornerRadius,
            color = color,
            overlayEnabled = overlayEnabled,
            bubbleAlpha = bubbleAlpha,
            maxWidth = maxWidth,
            onClick = onClick,
            animate = true,
        ) {"""
    if old_single in s:
        s = s.replace(old_single, new_single, 1)
        changed = True
        print("  single bubble keeps animate")

    if changed and s != orig:
        write(BUBBLE, s)
    else:
        print("BubbleSurface.kt: nothing matched")


def patch_chat_list():
    s = read(LIST)
    changed = False

    old_time = """                    if (showTimeHeader(displayNodes, index)) {
                        ChatTimeHeader(
                            text = formatTimeHeader(
                                node = node,
                                prevNode = displayNodes.getOrNull(index - 1),
                            )
                        )
                    }"""
    new_time = """                    val timeHeader = remember(node.id, index) {
                        if (showTimeHeader(displayNodes, index)) {
                            formatTimeHeader(
                                node = node,
                                prevNode = displayNodes.getOrNull(index - 1),
                            )
                        } else null
                    }
                    if (timeHeader != null) {
                        ChatTimeHeader(text = timeHeader)
                    }"""
    if old_time in s:
        s = s.replace(old_time, new_time)
        changed = True
        print("  time header -> remember")

    old_call = """                        ChatMessage(
                            node = node,
                            model = node.currentMessage.modelId?.let { settings.findModelById(it) },
                            assistant = settings.getAssistantById(conversation.assistantId),"""
    new_call = """                        val modelById = remember(node.currentMessage.modelId) {
                            node.currentMessage.modelId?.let { settings.findModelById(it) }
                        }
                        val assistantById = remember(conversation.assistantId) {
                            settings.getAssistantById(conversation.assistantId)
                        }
                        ChatMessage(
                            node = node,
                            model = modelById,
                            assistant = assistantById,"""
    if old_call in s:
        s = s.replace(old_call, new_call)
        changed = True
        print("  model/assistant lookup -> remember")

    if changed:
        write(LIST, s)
    else:
        print("ChatList.kt: nothing matched")


def main():
    for f in (MSG, BUBBLE, LIST):
        if not f.exists():
            print("missing:", f)
            sys.exit(1)
    patch_chat_message()
    patch_bubble_surface()
    patch_chat_list()
    print("done")


if __name__ == "__main__":
    main()
