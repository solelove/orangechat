#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 v2.2.3 基线（7b041d77）上修正头像排布（v7）。

目标形态（微信式，一条消息只一个头像，永远跟内容顶对齐）：
  - 不拆分气泡：外层画一个侧边头像，整条消息（文字+图片混排）共用这一个
  - 拆分气泡：外层不画，每个小气泡自己贴身像

v6 的失败（两层错叠在一起）：
  1) 外层 sideAvatarVisible 里留着基线的
     `message.parts.all { it is UIMessagePart.Text }`，一混图片外层就让位
  2) v6 脚本把 `segmentAvatar = ...` 无条件塞进 SplitBubbleColumn，
     绕过了基线 segmentAvatarFor 里的 willSplitIntoBubbles 判定，
     于是不拆分时内层也带头像，两个头像各跟各的行高，错开半个身位

v7 做法：
  1) 外层 sideAvatarVisible 只留 isEmptyUIMessage + shouldHideSideAvatar
  2) 文字段 / 非文本段的 segmentAvatar 重新受 willSplitIntoBubbles 管
  3) SplitBubbleColumn / PartRow 的 spec 保留，拆分时照常逐段画

所有历史形态都收敛到同一结果，锚点缺失直接失败不默默跳过。
"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessage.kt")
src = P.read_text(encoding="utf-8")

changed = []


def patch(old, new, tag, required=False):
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


# ==== 1) 外层侧边头像：删掉 all{Text}，只认 shouldHideSideAvatar ====
# 1a 带注释的完整形态（v6 写进去的那段）
patch(
    """    // 只有纯文本且没开拆分 才由外层画那唯一一个头像
    val sideAvatarVisible = remember(message.parts, assistant) {
        message.parts.all { it is UIMessagePart.Text } &&
            !message.parts.isEmptyUIMessage() &&
            !shouldHideSideAvatar(isUserMessage, assistant)
    }""",
    """    // 一条消息只画一个侧边头像：不拆分时外层画，拆分时让位给小气泡
    val sideAvatarVisible = remember(message.parts, assistant) {
        !message.parts.isEmptyUIMessage() &&
            !shouldHideSideAvatar(isUserMessage, assistant)
    }""",
    "outer-side",
)

# 1b 只替换表达式体（防止注释被改过）
patch(
    """        message.parts.all { it is UIMessagePart.Text } &&
            !message.parts.isEmptyUIMessage() &&
            !shouldHideSideAvatar(isUserMessage, assistant)""",
    """        !message.parts.isEmptyUIMessage() &&
            !shouldHideSideAvatar(isUserMessage, assistant)""",
    "outer-side-body",
)

# ==== 2) 用户侧文字段：包进拆分判定 ====
patch(
    """                                        onClick = { onUserMessageClick?.invoke() },
                                        segmentAvatar = if (displaySettings.showUserAvatar)
                                            SegmentAvatarSpec.User(displaySettings.userAvatar, displaySettings.userNickname)
                                        else null,
                                    ) { segment ->""",
    """                                        onClick = { onUserMessageClick?.invoke() },
                                        segmentAvatar = textSegmentAvatar,
                                    ) { segment ->""",
    "user-seg",
    required=True,
)

# ==== 3) 助手侧文字段：包进拆分判定 ====
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
    "assistant-seg",
    required=True,
)

# ==== 4) 补 textSegmentAvatar / partAvatarSpec 两个局部变量（如果基线没有）====
# v6 里 MessagePartsBlock 直接用了 willSplitIntoBubbles / hasNonText，
# 这里统一换成由 AvatarVisibility.kt 的 segmentAvatarFor 决定。
if "val textSegmentAvatar" not in src:
    print("[avatar] FAIL: textSegmentAvatar declaration missing, cannot wire")
    sys.exit(1)

P.write_text(src, encoding="utf-8")

# ==== 校验 ====
checks = {
    "no_all_text": "message.parts.all { it is UIMessagePart.Text } &&" not in src,
    "no_false": "if (false && " not in src,
    "outer_ok": "!message.parts.isEmptyUIMessage() &&\n            !shouldHideSideAvatar(isUserMessage, assistant)" in src,
    "user_uses_spec": "segmentAvatar = textSegmentAvatar,\n                                    ) { segment ->" in src or "segmentAvatar = textSegmentAvatar," in src,
    "assistant_uses_spec": "segmentAvatar = textSegmentAvatar,\n                                            avatarLoading = loading," in src or "segmentAvatar = textSegmentAvatar," in src,
    "partrow": "PartRow(partAvatarSpec, isUser, loading)" in src,
}
fails = [k for k, v in checks.items() if not v]
print("[avatar] changed: %s" % (", ".join(changed) if changed else "nothing"))
if fails:
    print("[avatar] FAIL verify: %s" % ", ".join(fails))
    sys.exit(1)
print("[avatar] verify OK")
