# -*- coding: utf-8 -*-
"""热路径优化 v2：用行号定位，避开字面误差"""

import pathlib
import sys

BASE = pathlib.Path("app/src/main/java/me/rerere/rikkahub")
MSG = BASE / "ui/components/message/ChatMessage.kt"
BUBBLE = BASE / "ui/components/message/BubbleSurface.kt"
LIST = BASE / "ui/pages/chat/ChatList.kt"


def lines(p):
    return p.read_text(encoding="utf-8").split("\n")


def save(p, ls):
    p.write_text("\n".join(ls), encoding="utf-8")
    print("saved:", p)


NEW_FONT = """    val fontFamily = remember(settings.chatFontFamily, settings.customFontPath) {
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
    }""".split("\n")

ZIP_CONST = 'private val ZipMarkRegex = Regex("\\\\[zip:[^\\\\]]+\\\\]", RegexOption.IGNORE_CASE)'


def find(ls, needle, start=0):
    for i in range(start, len(ls)):
        if needle in ls[i]:
            return i
    return -1


def patch_msg():
    ls = lines(MSG)
    i = find(ls, "val textStyle = LocalTextStyle.current.copy(")
    if i < 0:
        print("font NOT FOUND")
        return False
    # 找闭合: 从 i 往下，遇到单独一行 "    )" 结束
    j = i + 1
    while j < len(ls) and ls[j].strip() != ")":
        j += 1
    assert ls[j].strip() == ")", "font block end not found"
    ls[i:j + 1] = NEW_FONT
    print("font replaced lines", i + 1, "-", j + 1)

    k = find(ls, "val maxBubbleWidth = (screenWidth * 0.72f).dp")
    if k >= 0:
        ls[k] = "    val maxBubbleWidth = remember(screenWidth) { (screenWidth * 0.72f).dp }"
        print("maxBubbleWidth patched")

    z = find(ls, 'part.text.replace(Regex("\\\\[zip:')
    if z < 0:
        z = find(ls, "part.text.replace(Regex(")
    if z >= 0:
        indent = ls[z][:len(ls[z]) - len(ls[z].lstrip())]
        ls[z] = indent + 'part.text.replace(ZipMarkRegex, "")'
        print("zip call patched")

    a = find(ls, "fun ChatMessage(")
    if a >= 0:
        # 往回到 @Composable 上面插常量
        while a > 0 and ls[a - 1].strip() != "":
            a -= 1
        ls.insert(a, ZIP_CONST)
        ls.insert(a + 1, "")
        print("zip const inserted at", a + 1)

    save(MSG, ls)
    return True


def patch_bubble():
    ls = lines(BUBBLE)
    # 参数表加 animate
    i = find(ls, "onClick: (() -> Unit)? = null,")
    cnt = 0
    while i >= 0:
        cnt += 1
        if cnt == 2:
            ls.insert(i + 1, "    animate: Boolean = false,")
            print("animate param added")
            break
        i = find(ls, "onClick: (() -> Unit)? = null,", i + 1)

    # 去掉有图分支的 animateContentSize
    j = find(ls, ".animateContentSize()")
    if j >= 0 and ".clip(RoundedCornerShape(cornerRadius))" in ls[j + 1]:
        del ls[j]
        print("image branch animate removed")

    # 普通分支按 animate 判断
    j = find(ls, ".animateContentSize()")
    if j >= 0:
        indent = ls[j][:len(ls[j]) - len(ls[j].lstrip())]
        ls[j] = indent + ".then(if (animate) Modifier.animateContentSize() else Modifier)"
        print("plain branch conditional")

    # 单气泡传 animate = true
    j = find(ls, "maxWidth = maxWidth,")
    if j >= 0:
        indent = ls[j][:len(ls[j]) - len(ls[j].lstrip())]
        ls.insert(j + 1, indent + "animate = true,")
        print("single bubble animate=true")

    save(BUBBLE, ls)
    return True


def patch_list():
    ls = lines(LIST)
    i = find(ls, "if (showTimeHeader(displayNodes, index)) {")
    if i < 0:
        print("time header NOT FOUND")
        return False
    indent = ls[i][:len(ls[i]) - len(ls[i].lstrip())]
    # 找 if 块结束
    j = i + 1
    depth = 1
    while j < len(ls) and depth > 0:
        depth += ls[j].count("{") - ls[j].count("}")
        j += 1
    block = [
        indent + "val timeHeader = remember(node.id, index) {",
        indent + "    if (showTimeHeader(displayNodes, index)) {",
        indent + "        formatTimeHeader(",
        indent + "            node = node,",
        indent + "            prevNode = displayNodes.getOrNull(index - 1),",
        indent + "        )",
        indent + "    } else null",
        indent + "}",
        indent + "if (timeHeader != null) {",
        indent + "    ChatTimeHeader(text = timeHeader)",
        indent + "}",
    ]
    ls[i:j] = block
    print("time header replaced")

    m = find(ls, "model = node.currentMessage.modelId?.let { settings.findModelById(it) },")
    if m >= 0:
        ind = ls[m][:len(ls[m]) - len(ls[m].lstrip())]
        ls[m] = ind + "model = remember(node.currentMessage.modelId) {"
        ls.insert(m + 1, ind + "    node.currentMessage.modelId?.let { settings.findModelById(it) }")
        ls.insert(m + 2, ind + "},")
        print("model remember")

    n = find(ls, "assistant = settings.getAssistantById(conversation.assistantId),")
    if n >= 0:
        ind = ls[n][:len(ls[n]) - len(ls[n].lstrip())]
        ls[n] = ind + "assistant = remember(conversation.assistantId) {"
        ls.insert(n + 1, ind + "    settings.getAssistantById(conversation.assistantId)")
        ls.insert(n + 2, ind + "},")
        print("assistant remember")

    save(LIST, ls)
    return True


def main():
    ok = patch_msg() and patch_bubble() and patch_list()
    if not ok:
        sys.exit(1)
    print("all patched")


if __name__ == "__main__":
    main()
