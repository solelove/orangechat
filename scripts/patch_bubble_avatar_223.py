#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 v2.2.3 基线（7b041d77）上恢复「每段气泡都带头像」。

基线里 BubbleSurface.kt 已经有 SegmentAvatarSpec / SplitBubbleColumn(segmentAvatar=...)，
因此这里只改 ChatMessage.kt：
  1) 用户侧 SplitBubbleColumn 传入 segmentAvatar
  2) 助手侧 SplitBubbleColumn 传入 segmentAvatar
  3) 外层侧边头像只在「整条都是文字」时画（非文本段由 PartRow 自己带，避免重复）

判定方式：看 OLD 锚点在不在。
  - OLD 在 -> 替换（正常路径）
  - OLD 不在、NEW 在 -> 已经打过，跳过，仍然算成功
  - 两个都不在 -> 锚点变了，直接失败（不许默默跳过）
不用「某个字符串是否存在」这种宽泛判断，上一版就因为基线里本来就有
`segmentAvatar = when {` 而误判成已打过，一个字没改。
"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessage.kt")
src = P.read_text(encoding="utf-8")

changed = []


def patch(old, new, tag):
    """old -> new。old 在就替换；old 不在但 new 在算已打过；都不在则失败。"""
    global src
    if old in src:
        n = src.count(old)
        if n != 1:
            print("[avatar] FAIL %s: old anchor hits=%d (expect 1)" % (tag, n))
            sys.exit(1)
        src = src.replace(old, new, 1)
        changed.append(tag + ":replaced")
        return
    if new in src:
        print("[avatar] %s: already patched, skip" % tag)
        return
    print("[avatar] FAIL %s: neither old nor new anchor found" % tag)
    sys.exit(1)


# ---- 1) 用户侧 ----
patch(
    """                                        onClick = { onUserMessageClick?.invoke() },
                                    ) { segment ->""",
    """                                        onClick = { onUserMessageClick?.invoke() },
                                        segmentAvatar = if (displaySettings.showUserAvatar)
                                            SegmentAvatarSpec.User(displaySettings.userAvatar, displaySettings.userNickname)
                                        else null,
                                    ) { segment ->""",
    "user",
)

# ---- 2) 助手侧 ----
patch(
    """                                            maxWidth = maxBubbleWidth,
                                            alignment = Alignment.Start,
                                        ) { segment ->""",
    """                                            maxWidth = maxBubbleWidth,
                                            alignment = Alignment.Start,
                                            segmentAvatar = when {
                                                !displaySettings.showModelIcon -> null
                                                assistant != null && assistant.useAssistantAvatar ->
                                                    SegmentAvatarSpec.AssistantAvatar(assistant)
                                                model != null -> SegmentAvatarSpec.Model(model.modelId)
                                                else -> null
                                            },
                                            avatarLoading = loading,
                                        ) { segment ->""",
    "assistant",
)

# ---- 3) 外层侧边头像开关 ----
patch(
    """if (!isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false""",
    """if (!isUserMessage && message.parts.all { it is UIMessagePart.Text } && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false""",
    "outer-assistant",
)

patch(
    """if (isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true""",
    """if (isUserMessage && message.parts.all { it is UIMessagePart.Text } && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true""",
    "outer-user",
)

# ---- 结果校验：必须真的带上了传参 ----
ok_user = "segmentAvatar = if (displaySettings.showUserAvatar)" in src
ok_asst = """                                            alignment = Alignment.Start,
                                            segmentAvatar = when {""" in src
if not (ok_user and ok_asst):
    print("[avatar] FAIL verify: user=%s assistant=%s" % (ok_user, ok_asst))
    sys.exit(1)

P.write_text(src, encoding="utf-8")
print("[avatar] patched: %s" % (", ".join(changed) if changed else "nothing to do"))
print("[avatar] verify OK user=%s assistant=%s" % (ok_user, ok_asst))
