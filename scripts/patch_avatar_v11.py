#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2.2.3 基线（7b041d77）上改头像归属 v11：按拆分开关一刀切。

开了拆分 -> 每段自带（文字段 + 图片段）
没开拆分 -> 外层画唯一那一个，文字段和图片段都不画
"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessage.kt")
src = P.read_text(encoding="utf-8")
changed = []


def patch(old, new, tag):
    global src
    if old in src:
        n = src.count(old)
        if n != 1:
            print("[avatar] FAIL %s: anchor hits=%d" % (tag, n))
            sys.exit(1)
        src = src.replace(old, new, 1)
        changed.append(tag)
        return True
    if new in src:
        print("[avatar] %s: already patched" % tag)
        return True
    print("[avatar] FAIL %s: anchor not found" % tag)
    sys.exit(1)


# A) 外层：去掉 all{Text}
patch(
    "        if (!isUserMessage && message.parts.all { it is UIMessagePart.Text } "
    "&& !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false, "
    "settings.showUserAvatar, settings.showModelIcon, settings.showAssistantBubble, assistant)) {",
    "        if (!isUserMessage && sideAvatarVisible) {",
    "outer-assistant",
)
patch(
    "        if (isUserMessage && message.parts.all { it is UIMessagePart.Text } "
    "&& !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true, "
    "settings.showUserAvatar, settings.showModelIcon, settings.showAssistantBubble, assistant)) {",
    "        if (isUserMessage && sideAvatarVisible) {",
    "outer-user",
)

anchor = """    val isUserMessage = message.role == MessageRole.USER
    Row("""
inject = """    val isUserMessage = message.role == MessageRole.USER

    // 没开拆分 -> 外层画唯一那一个侧边头像（纯文字、带思考块、混合消息都一样）
    // 开了拆分 -> 外层让位，由每个小气泡自己带
    val sideAvatarVisible = remember(message.parts, assistant, settings) {
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

# B) MessagePartsBlock：建立 splitOn 与两个 gate 后的 spec
anchor2 = """    val groupedParts = remember(parts) { parts.groupMessageParts() }

    // 非文本段（图片/视频/音频/文档）旁边也画头像，不受拆分开关限制
    val partAvatarSpec: SegmentAvatarSpec? = remember(role, assistant, model, displaySettings) {
"""

inject2 = """    val groupedParts = remember(parts) { parts.groupMessageParts() }

    // 按拆分开关一刀切：没开拆分时文字段和图片段都不画，只剩外层那一个
    val isUser = role == MessageRole.USER
    val splitOn = willSplitIntoBubbles(isUser, assistant)

    // 文字段头像：只有开了拆分才自带
    val textSegmentAvatar: SegmentAvatarSpec? = remember(
        role, assistant, model, displaySettings, splitOn
    ) {
        if (!splitOn) null
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

    // 非文本段头像：同样只在开了拆分时自带，没开拆分交给外层
    val partAvatarSpec: SegmentAvatarSpec? = remember(
        role, assistant, model, displaySettings, splitOn
    ) {
        if (!splitOn) null
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
    // __OLD_BODY_START__
"""
patch(anchor2, inject2, "specs-head")

# 把旧的 partAvatarSpec 主体（紧跟其后的那段）整段删掉
old_body = """        if (role == MessageRole.USER) {
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
    val partAvatarLoading = loading"""
patch(old_body, "    // __OLD_BODY_END__\n    val partAvatarLoading = loading", "specs-body")

# C) 文字段换成 gate 后的变量
patch(
    """                                        segmentAvatar = if (displaySettings.showUserAvatar)
                                            SegmentAvatarSpec.User(displaySettings.userAvatar, displaySettings.userNickname)
                                        else null,""",
    "                                        segmentAvatar = textSegmentAvatar,",
    "user-text-seg",
)
patch(
    """                                            segmentAvatar = when {
                                                !displaySettings.showModelIcon -> null
                                                assistant != null && assistant.useAssistantAvatar ->
                                                    SegmentAvatarSpec.AssistantAvatar(assistant)
                                                model != null -> SegmentAvatarSpec.Model(model.modelId)
                                                else -> null
                                            },""",
    "                                            segmentAvatar = textSegmentAvatar,",
    "assistant-text-seg",
)

P.write_text(src, encoding="utf-8")

checks = {
    "sideAvatarVisible": "val sideAvatarVisible = remember(message.parts, assistant, settings) {" in src,
    "outer_user": "if (isUserMessage && sideAvatarVisible) {" in src,
    "outer_asst": "if (!isUserMessage && sideAvatarVisible) {" in src,
    "no_all_text": "message.parts.all { it is UIMessagePart.Text } &&" not in src,
    "has_splitOn": "val splitOn = willSplitIntoBubbles(isUser, assistant)" in src,
    "text_seg_var": "val textSegmentAvatar: SegmentAvatarSpec? = remember(" in src,
    "text_seg_gated": "if (!splitOn) null" in src,
    "text_seg_wired": "segmentAvatar = textSegmentAvatar," in src,
    "part_seg_gated": "val partAvatarSpec: SegmentAvatarSpec? = remember(" in src,
    "audio_intact": "internal fun AudioPlayerBubble(url: String) {" in src,
    "voice_intact": "internal fun VoiceMessageBubble(" in src,
}
fails = [k for k, v in checks.items() if not v]
print("[avatar] changed:", changed)
if fails:
    print("[avatar] FAIL verify:", ", ".join(fails))
    sys.exit(1)
print("[avatar] verify OK")
