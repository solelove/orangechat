# -*- coding: utf-8 -*-
"""热路径优化 v4：括号深度从 1 起算，避免首行即归零"""

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


def find(ls, needle, start=0):
    for i in range(start, len(ls)):
        if needle in ls[i]:
            return i
    return -1


NEW_FONT = [
    "    val fontFamily = remember(settings.chatFontFamily, settings.customFontPath) {",
    "        when (settings.chatFontFamily) {",
    "            ChatFontFamily.DEFAULT -> FontFamily.Default",
    "            ChatFontFamily.SERIF -> FontFamily.Serif",
    "            ChatFontFamily.MONOSPACE -> FontFamily.Monospace",
    "            ChatFontFamily.CUSTOM -> {",
    "                val customPath = settings.customFontPath",
    "                if (customPath.isNotBlank() && java.io.File(customPath).exists()) {",
    "                    FontFamily(Font(java.io.File(customPath)))",
    "                } else {",
    "                    FontFamily.Default",
    "                }",
    "            }",
    "        }",
    "    }",
    "    val baseTextStyle = LocalTextStyle.current",
    "    val textStyle = remember(baseTextStyle, settings.fontSizeRatio, settings.chatTextColor, fontFamily) {",
    "        baseTextStyle.copy(",
    "            fontSize = baseTextStyle.fontSize * settings.fontSizeRatio,",
    "            color = settings.chatTextColor?.let { it.toComposeColor() } ?: Color.Unspecified,",
    "            lineHeight = baseTextStyle.lineHeight * settings.fontSizeRatio,",
    "            fontFamily = fontFamily,",
    "        )",
    "    }",
]


def patch_msg():
    p = MSG
    ls = lines(p)
    orig = len(ls)

    i = find(ls, "val textStyle = LocalTextStyle.current.copy(")
    if i >= 0:
        # 从下一行开始数，深度起始 1（首行的 copy( 开启）
        depth = 1
        end = -1
        for j in range(i + 1, min(i + 40, len(ls))):
            depth += ls[j].count("(") - ls[j].count(")")
            if depth <= 0:
                end = j
                break
        if end > 0:
            ls[i:end + 1] = NEW_FONT
            print("font block replaced:", i + 1, "-", end + 1)
        else:
            print("font: end not found")
            sys.exit(1)
    else:
        print("font: already patched")

    if find(ls, "private val ZipMarkRegex") < 0:
        z = find(ls, 'part.text.replace(Regex(')
        if z >= 0:
            ind = ls[z][:len(ls[z]) - len(ls[z].lstrip())]
            ls[z] = ind + 'part.text.replace(ZipMarkRegex, "")'
            a = find(ls, "fun ChatMessage(")
            k = a
            while k > 0 and ls[k - 1].strip() != "":
                k -= 1
            ls.insert(k, 'private val ZipMarkRegex = Regex("\\\\[zip:[^\\\\]]+\\\\]", RegexOption.IGNORE_CASE)')
            ls.insert(k + 1, "")
            print("zip const inserted")
        else:
            print("zip: call not found")
    else:
        print("zip: already patched")

    m = find(ls, "val maxBubbleWidth = (screenWidth * 0.72f).dp")
    if m >= 0:
        ind = ls[m][:len(ls[m]) - len(ls[m].lstrip())]
        ls[m] = ind + "val maxBubbleWidth = remember(screenWidth) { (screenWidth * 0.72f).dp }"
        print("maxBubbleWidth patched")
    else:
        print("maxBubbleWidth: already patched")

    text = "\n".join(ls)
    if "fun ChatMessage(" not in text or len(ls) < orig - 60:
        print("ABORT msg: sanity fail", orig, len(ls))
        sys.exit(1)
    save(p, ls)


def patch_bubble():
    p = BUBBLE
    ls = lines(p)
    orig = len(ls)

    if find(ls, "animate: Boolean = false,") < 0:
        hits = []
        i = 0
        while True:
            i = find(ls, "onClick: (() -> Unit)? = null,", i)
            if i < 0:
                break
            hits.append(i)
            i += 1
        if len(hits) >= 2:
            t = hits[1]
            ind = ls[t][:len(ls[t]) - len(ls[t].lstrip())]
            ls.insert(t + 1, ind + "animate: Boolean = false,")
            print("bubble animate param added")
    else:
        print("bubble animate param exists")

    for idx in range(len(ls) - 1):
        if ".animateContentSize()" in ls[idx] and ".clip(RoundedCornerShape(cornerRadius))" in ls[idx + 1]:
            del ls[idx]
            print("bubble image branch animate removed")
            break

    j = find(ls, ".animateContentSize()")
    if j >= 0:
        ind = ls[j][:len(ls[j]) - len(ls[j].lstrip())]
        ls[j] = ind + ".then(if (animate) Modifier.animateContentSize() else Modifier)"
        print("bubble plain branch conditional")
    else:
        print("bubble plain branch already patched")

    j = find(ls, "maxWidth = maxWidth,")
    if j >= 0 and find(ls, "animate = true,") < 0:
        ind = ls[j][:len(ls[j]) - len(ls[j].lstrip())]
        ls.insert(j + 1, ind + "animate = true,")
        print("bubble single animate=true")
    else:
        print("bubble single already patched")

    if "fun BubbleSurface(" not in "\n".join(ls) or len(ls) < orig - 10:
        print("ABORT bubble sanity", orig, len(ls))
        sys.exit(1)
    save(p, ls)


def patch_list():
    p = LIST
    ls = lines(p)
    orig = len(ls)

    if find(ls, "val timeHeader = remember(node.id, index)") < 0:
        i = find(ls, "if (showTimeHeader(displayNodes, index)) {")
        if i >= 0:
            ind = ls[i][:len(ls[i]) - len(ls[i].lstrip())]
            depth = 0
            end = -1
            for j in range(i, min(i + 20, len(ls))):
                depth += ls[j].count("{") - ls[j].count("}")
                if depth == 0:
                    end = j
                    break
            if end > 0:
                block = [
                    ind + "val timeHeader = remember(node.id, index) {",
                    ind + "    if (showTimeHeader(displayNodes, index)) {",
                    ind + "        formatTimeHeader(",
                    ind + "            node = node,",
                    ind + "            prevNode = displayNodes.getOrNull(index - 1),",
                    ind + "        )",
                    ind + "    } else null",
                    ind + "}",
                    ind + "if (timeHeader != null) {",
                    ind + "    ChatTimeHeader(text = timeHeader)",
                    ind + "}",
                ]
                ls[i:end + 1] = block
                print("list time header remembered", i + 1, "-", end + 1)
            else:
                print("list time: end not found")
        else:
            print("list time: not found")
    else:
        print("list time: already patched")

    m = find(ls, "model = node.currentMessage.modelId?.let { settings.findModelById(it) },")
    if m >= 0:
        ind = ls[m][:len(ls[m]) - len(ls[m].lstrip())]
        ls[m:m + 1] = [
            ind + "model = remember(node.currentMessage.modelId) {",
            ind + "    node.currentMessage.modelId?.let { settings.findModelById(it) }",
            ind + "},",
        ]
        print("list model remembered")
    else:
        print("list model: already patched")

    n = find(ls, "assistant = settings.getAssistantById(conversation.assistantId),")
    if n >= 0:
        ind = ls[n][:len(ls[n]) - len(ls[n].lstrip())]
        ls[n:n + 1] = [
            ind + "assistant = remember(conversation.assistantId) {",
            ind + "    settings.getAssistantById(conversation.assistantId)",
            ind + "},",
        ]
        print("list assistant remembered")
    else:
        print("list assistant: already patched")

    if len(ls) < orig - 30:
        print("ABORT list sanity", orig, len(ls))
        sys.exit(1)
    save(p, ls)


def main():
    patch_msg()
    patch_bubble()
    patch_list()
    print("DONE")


if __name__ == "__main__":
    main()
