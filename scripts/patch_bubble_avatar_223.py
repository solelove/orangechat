#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 v2.2.3 基线（7b041d77）上恢复「每个气泡段自己带一个头像」。

目标形态（微信式逐段头像）：
  - 每个文字气泡段带头像（SplitBubbleColumn 的 segmentAvatar）
  - 每个图片/视频/音频/文档段带头像（PartRow 的 spec）
  - 外层那条「整条消息一个侧边头像」彻底不画，否则纯文字消息会变成两个头像

上一版失败的根因：
  外层条件加了 `message.parts.all { it is UIMessagePart.Text }`，
  只要这条消息里混了图片，整条就不画侧边头像。
  而文字段头像是靠 SplitBubbleColumn 画的，一旦 MessagePartsBlock 里
  文字段前后的布局被外层 Row 撑开，视觉上就只剩图片那个头像。
  这次把外层侧边头像整个关掉，头像全交给内层逐段画，且只画一次。

判定方式：看 OLD 锚点在不在。
  - OLD 在 -> 替换（正常路径）
  - OLD 不在、NEW 在 -> 已经打过，跳过，仍然算成功
  - 两个都不在 -> 锚点变了，直接失败（不许默默跳过）
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


# ---- 1) 用户侧文字段带头像 ----
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

# ---- 2) 助手侧文字段带头像 ----
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

# ---- 3) 外层侧边头像：彻底不画 ----
disabled = 0
for old in (
    "if (!isUserMessage && message.parts.all { it is UIMessagePart.Text } && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false",
    "if (!isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false",
):
    if old in src:
        src = src.replace(
            old,
            "if (false && !isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false",
            1,
        )
        changed.append("outer-assistant:disabled")
        disabled += 1
        break

for old in (
    "if (isUserMessage && message.parts.all { it is UIMessagePart.Text } && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true",
    "if (isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true",
):
    if old in src:
        src = src.replace(
            old,
            "if (false && isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true",
            1,
        )
        changed.append("outer-user:disabled")
        disabled += 1
        break

# ---- 结果校验 ----
ok_user = "segmentAvatar = if (displaySettings.showUserAvatar)" in src
ok_asst = """                                            alignment = Alignment.Start,
                                            segmentAvatar = when {""" in src
ok_outer = "if (false && !isUserMessage" in src and "if (false && isUserMessage" in src
if not (ok_user and ok_asst and ok_outer):
    print("[avatar] FAIL verify: user=%s assistant=%s outer_off=%s" % (ok_user, ok_asst, ok_outer))
    sys.exit(1)

P.write_text(src, encoding="utf-8")
print("[avatar] patched: %s" % (", ".join(changed) if changed else "nothing to do"))
print("[avatar] verify OK user=%s assistant=%s outer_off=%s" % (ok_user, ok_asst, ok_outer))
