#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 v2.2.3 基线（7b041d77）上修正头像排布（v10）。

【基线 7b041d77 是「一条消息两个头像」】
  1) 外层侧边头像带 `message.parts.all { it is UIMessagePart.Text }`，
     要求整条消息全是文字段才画。混了图片、或带思考块，外层直接不画。
  2) 文字段 SplitBubbleColumn 的 segmentAvatar 是无条件的。
  3) 图片等非文本段 PartRow 的 partAvatarSpec 也是无条件的。
  => 文字+图片，内层同时画两个，错开半格。
  => 带思考块的纯文字，外层不画、内层也不给，一个没有。

【历次教训】
  v8：内层收紧到「只拆分才给」-> 带思考块的纯文字消息头像全没了。
  v9：外层去掉 all{Text} -> 纯文字好了，但混排里图片段也没头像了。

【v10 定案：按「段类型」分开判，不再一刀切】
  外层侧边头像：消息不空 且 没开拆分 -> 画（纯文字、带思考块、混排都算）。
  文字段头像  ：只有真拆分时才给（不然和外层重复）。
  非文本段头像：永远给（图片/视频/音频/文档 自己带一个，紧贴自己的行）。
  结果：
    纯文字不拆分  -> 外层一个，顶部对齐。
    带思考块不拆分-> 外层一个（思考块不占头像）。
    混排不拆分    -> 外层顶上 + 图片段自己一个。
    开了拆分      -> 外层让位，每段各自带。
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


# ==== A) 外层：基线四处条件收拢成 sideAvatarVisible（不带 all{Text}）====
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

patch(base_asst, "        if (!isUserMessage && sideAvatarVisible) {", "assistant-outer")
patch(base_user, "        if (isUserMessage && sideAvatarVisible) {", "user-outer")

anchor = """    val isUserMessage = message.role == MessageRole.USER
    Row("""
inject = """    val isUserMessage = message.role == MessageRole.USER

    // 一条消息顶部那个侧边头像：
    //   - 没开拆分 -> 由它负责（不管里面有没有图片、有没有思考块）
    //   - 开了拆分 -> 让位，由每个小气泡自己带
    val sideAvatarVisible = remember(message.parts, assistant) {
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

# ==== C) 拆成 textSegmentAvatar（拆分才给）+ partAvatarSpec（永远给）====
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
    """    val splitMode0 = willSplitIntoBubbles(role == MessageRole.USER, assistant)

    // 文字段头像：只在真拆分时才给；不拆分时由外层顶部那一个负责
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

    // 非文本段（图片/视频/音频/文档）头像：永远给，紧贴自己那一行，
    // 不受拆分开关影响——图片旁边不能没有头像
    val partAvatarSpec: SegmentAvatarSpec? = remember(role, assistant, model, displaySettings) {
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
    val partAvatarLoading = loading""",
    "segment-specs",
)

P.write_text(src, encoding="utf-8")

# ==== 校验 ====
checks = {
    "has_sideAvatarVisible": "val sideAvatarVisible = remember(message.parts, assistant)" in src,
    "outer_user_uses": "if (isUserMessage && sideAvatarVisible) {" in src,
    "outer_asst_uses": "if (!isUserMessage && sideAvatarVisible) {" in src,
    "outer_no_all_text": "message.parts.all { it is UIMessagePart.Text } &&" not in src,
    "text_seg_var": "val textSegmentAvatar: SegmentAvatarSpec? = remember(" in src,
    "text_seg_gated": "if (!splitMode0) null" in src,
    "text_seg_wired": "segmentAvatar = textSegmentAvatar," in src,
    "partrow_kept": "PartRow(\n                            spec = partAvatarSpec," in src,
    "part_not_gated": "// 非文本段（图片/视频/音频/文档）头像：永远给" in src,
    "no_mixed": "|| hasNonText" not in src,
    "no_false": "if (false && " not in src,
}
fails = [k for k, v in checks.items() if not v]
print("[avatar] changed: %s" % (", ".join(changed) if changed else "nothing"))
if fails:
    print("[avatar] FAIL verify: %s" % ", ".join(fails))
    sys.exit(1)
print("[avatar] verify OK")
