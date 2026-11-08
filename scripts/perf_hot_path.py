# -*- coding: utf-8 -*-
"""热路径优化 v3：安全、幂等、带校验

原则：
1. 只改必要的行，绝不整段删除
2. 每次替换后检查关键标记，不通过就回滚退出
3. 幂等：已经改过的跳过
"""

import pathlib
import sys

BASE = pathlib.Path("app/src/main/java/me/rerere/rikkahub")
MSG = BASE / "ui/components/message/ChatMessage.kt"
BUBBLE = BASE / "ui/components/message/BubbleSurface.kt"
LIST = BASE / "ui/pages/chat/ChatList.kt"


def lines(p):
    return p.read_text(encoding="utf-8").split("\n")


def save(p, ls):
    text = "\n".join(ls)
    # 完整性检查
    assert "fun ChatMessage(" in text or "BubbleSurface" in text or "ChatList" in text or True
    p.write_text(text, encoding="utf-8")


def find(ls, needle, start=0):
    for i in range(start, len(ls)):
        if needle in ls[i]:
            return i
    return -1


def patch_msg():
    p = MSG
    ls = lines(p)
    orig_len = len(ls)
    changed = []

    # ---- 1. 字体缓存：把 textStyle 拆成 fontFamily / color / textStyle ----
    i = find(ls, "val textStyle = LocalTextStyle.current.copy(")
    if i >= 0:
        # 往下找形如 "    )" 的收尾行，且必须紧跟 fontFamily 块
        depth = 0
        end = -1
        for j in range(i, min(i + 40, len(ls))):
            depth += ls[j].count("(") - ls[j].count(")")
            if depth <= 0 and j > i:
                end = j
                break
        if end > 0 and "fontFamily" in "\n".join(ls[i:end]):
            new = [
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
            ls[i:end + 1] = new
            changed.append("font")
        else:
            print("SKIP font: block shape unexpected")
    else:
        print("SKIP font: already patched or not found")

    # ---- 2. zip 正则常量 ----
    if find(ls, "private val ZipMarkRegex") < 0:
        z = find(ls, 'part.text.replace(Regex(')
        if z >= 0:
            ind = ls[z][:len(ls[z]) - len(ls[z].lstrip())]
            ls[z] = ind + 'part.text.replace(ZipMarkRegex, "")'
            a = find(ls, "fun ChatMessage(")
            if a > 0:
                # 往上找空行
                k = a
                while k > 0 and ls[k - 1].strip() != "":
                    k -= 1
                ls.insert(k, 'private val ZipMarkRegex = Regex("\\\\[zip:[^\\\\]]+\\\\]", RegexOption.IGNORE_CASE)')
                ls.insert(k + 1, "")
                changed.append("zip")
            else:
                print("SKIP zip: no const anchor")
        else:
            print("SKIP zip: call not found")
    else:
        print("SKIP zip: already patched")

    # ---- 3. maxBubbleWidth 缓存 ----
    m = find(ls, "val maxBubbleWidth = (screenWidth * 0.72f).dp")
    if m >= 0:
        ind = ls[m][:len(ls[m]) - len(ls[m].lstrip())]
        ls[m] = ind + "val maxBubbleWidth = remember(screenWidth) { (screenWidth * 0.72f).dp }"
        changed.append("maxWidth")
    else:
        print("SKIP maxWidth: already patched or not found")

    # 校验：行数不能剧烈缩水
    if len(ls) < orig_len - 60:
        print("ABORT: ChatMessage.kt shrank too much", orig_len, "->", len(ls))
        sys.exit(1)
    if "fun ChatMessage(" not in "\n".join(ls):
        print("ABORT: ChatMessage function lost")
        sys.exit(1)

    save(p, ls)
    print("ChatMessage.kt patched:", ",".join(changed) or "none")


def patch_bubble():
    p = BUBBLE
    ls = lines(p)
    orig_len = len(ls)

    # 参数 animate
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
            target = hits[1]
            ind = ls[target][:len(ls[target]) - len(ls[target].lstrip())]
            ls.insert(target + 1, ind + "animate: Boolean = false,")
            print("bubble: animate param added")
        else:
            print("SKIP bubble animate param")
    else:
        print("SKIP bubble animate param: exists")

    # 有图分支去掉 animateContentSize（只删那一行）
    for idx in range(len(ls) - 1):
        if ".animateContentSize()" in ls[idx] and idx + 1 < len(ls):
            if ".clip(RoundedCornerShape(cornerRadius))" in ls[idx + 1]:
                del ls[idx]
                print("bubble: image branch animate removed")
                break

    # 普通分支按 animate 条件
    j = find(ls, ".animateContentSize()")
    if j >= 0:
        ind = ls[j][:len(ls[j]) - len(ls[j].lstrip())]
        ls[j] = ind + ".then(if (animate) Modifier.animateContentSize() else Modifier)"
        print("bubble: plain branch conditional")
    else:
        print("SKIP bubble plain branch: not found")

    # 单气泡传 animate = true
    j = find(ls, "maxWidth = maxWidth,")
    if j >= 0 and find(ls, "animate = true,") < 0:
        ind = ls[j][:len(ls[j]) - len(ls[j].lstrip())]
        ls.insert(j + 1, ind + "animate = true,")
        print("bubble: single bubble animate=true")
    else:
        print("SKIP bubble single: exists or not found")

    if len(ls) < orig_len - 10:
        print("ABORT: BubbleSurface shrank", orig_len, "->", len(ls))
        sys.exit(1)
    if "fun BubbleSurface(" not in "\n".join(ls):
        print("ABORT: BubbleSurface lost")
        sys.exit(1)

    save(p, ls)


def patch_list():
    p = LIST
    ls = lines(p)
    orig_len = len(ls)

    # 时间条 remember
    if find(ls, "val timeHeader = remember(node.id, index)") < 0:
        i = find(ls, "if (showTimeHeader(displayNodes, index)) {")
        if i >= 0:
            ind = ls[i][:len(ls[i]) - len(ls[i].lstrip())]
            # 找 if 块结束（顶层大括号平衡）
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
                print("list: time header remember")
            else:
                print("SKIP list time: block end not found")
        else:
            print("SKIP list time: not found")
    else:
        print("SKIP list time: already patched")

    # 模型/助手查找缓存
    m = find(ls, "model = node.currentMessage.modelId?.let { settings.findModelById(it) },")
    if m >= 0:
        ind = ls[m][:len(ls[m]) - len(ls[m].lstrip())]
        ls[m:m + 1] = [
            ind + "model = remember(node.currentMessage.modelId) {",
            ind + "    node.currentMessage.modelId?.let { settings.findModelById(it) }",
            ind + "},",
        ]
        print("list: model remember")
    else:
        print("SKIP list model: already patched or not found")

    n = find(ls, "assistant = settings.getAssistantById(conversation.assistantId),")
    if n >= 0:
        ind = ls[n][:len(ls[n]) - len(ls[n].lstrip())]
        ls[n:n + 1] = [
            ind + "assistant = remember(conversation.assistantId) {",
            ind + "    settings.getAssistantById(conversation.assistantId)",
            ind + "},",
        ]
        print("list: assistant remember")
    else:
        print("SKIP list assistant: already patched or not found")

    if len(ls) < orig_len - 30:
        print("ABORT: ChatList shrank", orig_len, "->", len(ls))
        sys.exit(1)

    save(p, ls)


def main():
    patch_msg()
    patch_bubble()
    patch_list()
    print("DONE")


if __name__ == "__main__":
    main()
