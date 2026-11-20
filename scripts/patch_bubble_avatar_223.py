#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 v2.2.3 基线（7b041d77）上修正头像排布（v8）。

【根因，写清楚了免得再绕】
基线 7b041d77 的 ChatMessage.kt 本来就是「一条消息两个头像」：

  1) 外层侧边头像带 `message.parts.all { it is UIMessagePart.Text }`，
     纯文字才画。混了图片，外层就让位。
  2) 文字段 SplitBubbleColumn 的 segmentAvatar 是无条件的
     `if (displaySettings.showUserAvatar) SegmentAvatarSpec.User(...)`，
     不看拆分。
  3) 图片等非文本段 PartRow 的 partAvatarSpec 也是无条件的。

于是「文字+图片」的消息里，内层会同时画出文字段头像和图片段头像，
两者各自跟着自己那一行的高度走，图片行高、文字行矮，视觉上错开半格。

之前几版一直在改外层的 all{Text}，方向全错——外层本来就没问题，
问题在内层多发了一个头像。

【v8 做法】
  A) 外层侧边头像：维持基线的 all{Text} 语义，但改用 shouldHideSideAvatar
     统一判（值等价，不引入新分支）。这条消息是纯文字、又没开拆分 -> 画一个。
  B) 文字段 segmentAvatar：只在真拆分（willSplitIntoBubbles）时才给。
  C) 非文本段 partAvatarSpec：同样只在真拆分时才给。

结果：不拆分时，一条消息只有外层那一个头像，跟气泡顶部对齐；
拆分时外层不画，每段自己带自己的。
"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessage.kt")
src = P.read_text(encoding="utf-8")

changed = []


def patch(old, new, tag, required=True):
    global src
    if old in src:
        n = src.count(old)
        if n != 1:
            print("[avatar] FAIL %s: old anchor hits=%d (expect 1)" % (tag, n))
            sys.exit(1)
        src = src.replace(old, new, 1)
        changed.append(tag + ":replaced")
        return True
    if new in src:
        print("[avatar] %s: already patched, skip" % tag)
        return True
    if required:
        print("[avatar] FAIL %s: neither old nor new anchor found" % tag)
        sys.exit(1)
    print("[avatar] %s: anchor absent" % tag)
    return False


# ==== A) 外层侧边头像：基线四处条件收拢成一个 sideAvatarVisible ====
# 基线原文（助手侧 / 用户侧）
base_asst = (
    "        if (!isUserMessage && message.parts.all { it is UIMessagePart.Text } "
    "&& !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false, "
    "settings.showUserAvatar, settings.showModelIcon, settings.showAssistantBubble, assistant)) {"
)
base_user = (
    "        if (isUserMessage && message.parts.all { it is UIMessagePart.Text } "
    "&& !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true, "
    "settings.showUserAvatar, settings.showModelIcon, settings.showAssistantBubble, assistant)) {"
)

new_asst = "        if (!isUserMessage && sideAvatarVisible) {"
new_user = "        if (isUserMessage && sideAvatarVisible) {"

patch(base_asst, new_asst, "assistant-outer")
patch(base_user, new_user, "user-outer")

# 在 Row(...) 之前插入 sideAvatarVisible 定义
anchor = """    val isUserMessage = message.role == MessageRole.USER
    Row("""
inject = """    val isUserMessage = message.role == MessageRole.USER

    // 一条消息只画一个头像：纯文字且没开拆分时由外层画；拆分时让位给小气泡
    val sideAvatarVisible = remember(message.parts, assistant) {
        message.parts.all { it is UIMessagePart.Text } &&
            !message.parts.isEmptyUIMessage() &&
            !shouldHideSideAvatar(
                isUser = isUserMessage,
                showUserAvatar = settings.showUserAvatar,
                showModelIcon = settings.showModelIcon,
                showAssistantBubble = settings.showAssistantBubble,
                assistant = assistant,
            )
    }

    Row("""
patch(anchor, inject, "sideAvatarVisible")

# ==== B) 文字段头像：无条件 -> 只在真拆分的才给 ====
patch(
    """                                        onClick = { onUserMessageClick?.invoke() },
                                        segmentAvatar = if (displaySettings.showUserAvatar)
                                            SegmentAvatarSpec.User(displaySettings.userAvatar, displaySettings.userNickname)
                                        else null,
                                    ) { segment ->""",
    """                                        onClick = { onUserMessageClick?.invoke() },
                                        segmentAvatar = textSegmentAvatar,
                                    ) { segment ->""",
    "user-text-seg",
)

patch(
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
    """                                            maxWidth = maxBubbleWidth,
                                            alignment = Alignment.Start,
                                            segmentAvatar = textSegmentAvatar,
                                            avatarLoading = loading,
                                        ) { segment ->""",
    "assistant-text-seg",
)

# ==== C) 非文本段头像：无条件 -> 只在真拆分的才给 ====
patch(
    """    // 非文本段（图片/视频/音频/文档）旁边也画头像，不受拆分开关限制
    val partAvatarSpec: SegmentAvatarSpec? = remember(role, assistant, model, displaySettings) {
        if (role == MessageRole.USER) {
            if (displaySettings.showUserAvatar) {
                SegmentAvatarSpec.User(displaySettings.userAvatar, displaySettings.userNickname)
            } else null
        } else {
            if (!displaySettings.showModelIcon) null
            else when {
                assistant != null && assistant.useAssistantAvatar ->
                    SegmentAvatarSpec.AssistantAvatar(assistant)
                model != null -> SegmentAvatarSpec.Model(model.modelId)
                else -> null
            }
        }
    }
    val partAvatarLoading = loading""",
    """    // 文字段头像：只在真拆分时才逐段给；不拆分时整条消息由外层那一个负责
    val splitMode0 = willSplitIntoBubbles(role == MessageRole.USER, assistant)
    val textSegmentAvatar: SegmentAvatarSpec? = remember(
        role, assistant, model, displaySettings, splitMode0
    ) {
        if (!splitMode0) null
        else if (role == MessageRole.USER) {
            if (displaySettings.showUserAvatar)
                SegmentAvatarSpec.User(displaySettings.userAvatar, displaySettings.userNickname)
            else null
        } else {
            if (!displaySettings.showModelIcon) null
            else when {
                assistant != null && assistant.useAssistantAvatar ->
                    SegmentAvatarSpec.AssistantAvatar(assistant)
                model != null -> SegmentAvatarSpec.Model(model.modelId)
                else -> null
            }
        }
    }

    // 非文本段（图片/视频/音频/文档）头像：同样只在真拆分时才给
    val partAvatarSpec: SegmentAvatarSpec? = remember(
        role, assistant, model, displaySettings, splitMode0
    ) {
        if (!splitMode0) null
        else if (role == MessageRole.USER) {
            if (displaySettings.showUserAvatar)
                SegmentAvatarSpec.User(displaySettings.userAvatar, displaySettings.userNickname)
            else null
        } else {
            if (!displaySettings.showModelIcon) null
            else when {
                assistant != null && assistant.useAssistantAvatar ->
                    SegmentAvatarSpec.AssistantAvatar(assistant)
                model != null -> SegmentAvatarSpec.Model(model.modelId)
                else -> null
            }
        }
    }
    val partAvatarLoading = loading""",
    "segment-specs",
)

P.write_text(src, encoding="utf-8")

# ==== 校验 ====
checks = {
    "has_sideAvatarVisible": "val sideAvatarVisible = remember(message.parts, assistant)" in src,
    "outer_user_uses": "if (isUserMessage && sideAvatarVisible) {" in src,
    "outer_asst_uses": "if (!isUserMessage && sideAvatarVisible) {" in src,
    "no_inline_outer": "message.parts.all { it is UIMessagePart.Text } && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(" not in src,
    "text_seg_var": "val textSegmentAvatar: SegmentAvatarSpec? = remember(" in src,
    "text_seg_wired_user": "segmentAvatar = textSegmentAvatar," in src,
    "partrow_unchanged": "PartRow(\n                            spec = partAvatarSpec," in src,
    "no_mixed": "|| hasNonText" not in src,
    "no_false": "if (false && " not in src,
}
fails = [k for k, v in checks.items() if not v]
print("[avatar] changed: %s" % (", ".join(changed) if changed else "nothing"))
if fails:
    print("[avatar] FAIL verify: %s" % ", ".join(fails))
    sys.exit(1)
print("[avatar] verify OK")
