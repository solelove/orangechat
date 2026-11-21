#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2.2.3 基线（7b041d77）上的头像归属 v12。

用户定案（2026-11-21）：
  不开拆分的时候也要「每个段自己带一个头像」——
  文字段一个、图片段一个，各对齐自己那一块，位置不齐也无所谓。
  思考块/工具块不带头像。外层侧边头像彻底不画（避免和段头像重复）。

做法：
  1) 外层两个 if(!isUserMessage && ...) 分支整段删掉（连同 Spacer）
  2) 文字段 segmentAvatar 无条件给（不看拆分开关）
  3) 非文本段 partAvatarSpec 无条件给（不看拆分开关）
"""
import pathlib
import re
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


# ========== 1) 外层：删掉助手侧边头像整块 ==========
old_asst = (
    "        if (!isUserMessage && message.parts.all { it is UIMessagePart.Text } "
    "&& !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false, "
    "settings.showUserAvatar, settings.showModelIcon, settings.showAssistantBubble, assistant)) {\n"
    "            ChatMessageSideAvatar(\n"
    "                message = message,\n"
    "                model = model,\n"
    "                assistant = assistant,\n"
    "                loading = loading,\n"
    "            )\n"
    "            Spacer(modifier = Modifier.width(8.dp))\n"
    "        }\n"
)
patch(old_asst, "", "drop-outer-assistant")

# ========== 2) 外层：删掉用户侧边头像整块 ==========
old_user = (
    "        if (isUserMessage && message.parts.all { it is UIMessagePart.Text } "
    "&& !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true, "
    "settings.showUserAvatar, settings.showModelIcon, settings.showAssistantBubble, assistant)) {\n"
    "            Spacer(modifier = Modifier.width(8.dp))\n"
    "            ChatMessageSideUserAvatar(\n"
    "                message = message,\n"
    "                avatar = settings.userAvatar,\n"
    "                nickname = settings.userNickname,\n"
    "            )\n"
    "        }\n"
)
patch(old_user, "", "drop-outer-user")

# ========== 3) 文字段 / 非文本段头像：无条件给（不看拆分开关）==========
anchor = """    val groupedParts = remember(parts) { parts.groupMessageParts() }

    // 非文本段（图片/视频/音频/文档）旁边也画头像，不受拆分开关限制
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
    val partAvatarLoading = loading"""

inject = """    val groupedParts = remember(parts) { parts.groupMessageParts() }

    // v12：不管开没开拆分，文字段和图片段都各自带一个头像。
    // 思考块、工具块不带；外层侧边头像已经删掉，不会重复。
    val textSegmentAvatar: SegmentAvatarSpec? = remember(
        role, assistant, model, displaySettings
    ) {
        if (role == MessageRole.USER) {
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
    val partAvatarSpec: SegmentAvatarSpec? = textSegmentAvatar
    val partAvatarLoading = loading"""
patch(anchor, inject, "specs")

# ========== 4) 文字段改用 textSegmentAvatar ==========
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

# ---- 顺带：外层删掉后 ChatMessageSideAvatar/SideUserAvatar 可能变成未使用 ----
# Kotlin 私有未使用函数只是 warning，不影响编译，保持原样。

checks = {
    "outer_asst_gone": "ChatMessageSideAvatar(\n                message = message," not in src,
    "outer_user_gone": "ChatMessageSideUserAvatar(\n                message = message," not in src,
    "no_shouldHideSideAvatar_call": "!shouldHideSideAvatar(" not in src,
    "text_seg_var": "val textSegmentAvatar: SegmentAvatarSpec? = remember(" in src,
    "text_seg_wired": "segmentAvatar = textSegmentAvatar," in src,
    "part_from_text": "val partAvatarSpec: SegmentAvatarSpec? = textSegmentAvatar" in src,
    "audio_intact": "internal fun AudioPlayerBubble(url: String) {" in src,
    "voice_intact": "internal fun VoiceMessageBubble(" in src,
    "thinking_no_avatar": "ChatMessageReasoningStep(" in src,
}
fails = [k for k, v in checks.items() if not v]
print("[avatar] changed:", changed)
if fails:
    print("[avatar] FAIL verify:", ", ".join(fails))
    sys.exit(1)
print("[avatar] verify OK")
