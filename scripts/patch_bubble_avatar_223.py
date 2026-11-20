#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 v2.2.3 基线（7b041d77）上恢复「每段气泡都带头像」。

BubbleSurface.kt 基线里已经有 SegmentAvatarSpec / SplitBubbleColumn(segmentAvatar=...)，
因此这里只改 ChatMessage.kt 两处：
  1) 用户侧 / 助手侧 SplitBubbleColumn 传入 segmentAvatar
  2) 外层侧边头像不再因为「有非文本段」就隐藏，改回按原逻辑（文字整条才画侧头像 +
     非文本段由 PartRow 自己画），拆分成多段时由 SplitBubbleColumn 逐段画
"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessage.kt")
src = P.read_text(encoding="utf-8")
orig = src

changed = []


def sub(old, new, tag, count=1):
    global src
    hits = src.count(old)
    if hits != count:
        print("[avatar] locate failed: %s hits=%d (expect %d)" % (tag, hits, count))
        sys.exit(1)
    src = src.replace(old, new)
    changed.append(tag)


# ---- 1) 用户侧：传 segmentAvatar ----
OLD_USER = """                                        onClick = { onUserMessageClick?.invoke() },
                                    ) { segment ->"""
NEW_USER = """                                        onClick = { onUserMessageClick?.invoke() },
                                        segmentAvatar = if (displaySettings.showUserAvatar)
                                            SegmentAvatarSpec.User(displaySettings.userAvatar, displaySettings.userNickname)
                                        else null,
                                    ) { segment ->"""
if "segmentAvatar = if (displaySettings.showUserAvatar)" not in src:
    sub(OLD_USER, NEW_USER, "user segmentAvatar")
else:
    print("[avatar] user segmentAvatar already present, skip")

# ---- 2) 助手侧：传 segmentAvatar ----
OLD_ASST = """                                            maxWidth = maxBubbleWidth,
                                            alignment = Alignment.Start,
                                        ) { segment ->"""
NEW_ASST = """                                            maxWidth = maxBubbleWidth,
                                            alignment = Alignment.Start,
                                            segmentAvatar = when {
                                                !displaySettings.showModelIcon -> null
                                                assistant != null && assistant.useAssistantAvatar ->
                                                    SegmentAvatarSpec.AssistantAvatar(assistant)
                                                model != null -> SegmentAvatarSpec.Model(model.modelId)
                                                else -> null
                                            },
                                            avatarLoading = loading,
                                        ) { segment ->"""
if "segmentAvatar = when {" not in src:
    sub(OLD_ASST, NEW_ASST, "assistant segmentAvatar")
else:
    print("[avatar] assistant segmentAvatar already present, skip")

# ---- 3) 外层侧边头像：有非文本段时不再画，交给 PartRow / SplitBubbleColumn ----
OLD_OUT_ASST = "if (!isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false"
NEW_OUT_ASST = "if (!isUserMessage && message.parts.all { it is UIMessagePart.Text } && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false"
if OLD_OUT_ASST in src:
    sub(OLD_OUT_ASST, NEW_OUT_ASST, "outer assistant avatar gate")

OLD_OUT_USER = "if (isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true"
NEW_OUT_USER = "if (isUserMessage && message.parts.all { it is UIMessagePart.Text } && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true"
if OLD_OUT_USER in src:
    sub(OLD_OUT_USER, NEW_OUT_USER, "outer user avatar gate")

if src == orig:
    print("[avatar] no change at all")
    sys.exit(1)

P.write_text(src, encoding="utf-8")
print("[avatar] patched:", ", ".join(changed))
