#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 v2.2.3 基线（7b041d77）上恢复头像显示（v6：恢复侧边头像，只在拆分时隐藏）。

目标形态（微信式）：
  - 不拆分气泡时：外层整条消息旁边画一个侧边头像（文字段、图片段都算这一条消息）
  - 拆分气泡时：外层不画，改由每个小气泡自己贴身像（SplitBubbleColumn 的 segmentAvatar）
  - 非文本段（图片/视频/音频/文档）：拆分模式时自己带一个头像（PartRow 的 spec）

v5 的失败：把外层侧边头像写成 `if (false && ...)` 彻底关掉，
结果关掉拆分开关后全都不画，用户两端都没头像。基线原代码的空头像根因是
`message.parts.all { it is UIMessagePart.Text }` 这个额外限制——只要消息里混了
非文字段，侧边头像就不画；而 NONE 模式那段 SplitBubbleColumn 直接 return 走
BubbleSurface，segmentAvatar 根本没用上。
所以正解是：删掉 `all{Text}` 限制，让 shouldHideSideAvatar 决定是否画，
它只在「真要拆分且逐段头像会显示」时才返回 true。

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

# ---- 3) 外层侧边头像：去掉「全是文字段才画」的额外限制，交给 shouldHideSideAvatar ---
def restore_outer(prefix, tag):
    """把外层条件恢复成只剩 shouldHideSideAvatar 判定，兼容 v5 的 if(false&&) 形态。"""
    global src
    candidates = [
        # v5 留下的彻底禁用形态
        "if (false && " + prefix + " && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(",
        # 基线原始形态（带 all{Text}）
        "if (" + prefix + " && message.parts.all { it is UIMessagePart.Text } && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(",
        # 已经修好的形态
        "if (" + prefix + " && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(",
    ]
    for c in candidates:
        if c in src:
            if c.startswith("if (" + prefix + " && !message.parts.isEmptyUIMessage()"):
                print("[avatar] %s: already patched, skip" % tag)
                return
            n = src.count(c)
            if n != 1:
                print("[avatar] FAIL %s: anchor hits=%d (expect 1)" % (tag, n))
                sys.exit(1)
            src = src.replace(
                c,
                "if (" + prefix + " && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(",
                1,
            )
            changed.append(tag + ":restored")
            return
    print("[avatar] FAIL %s: no outer anchor matched" % tag)
    sys.exit(1)


restore_outer("!isUserMessage", "outer-assistant")
restore_outer("isUserMessage", "outer-user")

# ---- 结果校验 ----
ok_user = "segmentAvatar = if (displaySettings.showUserAvatar)" in src
ok_asst = """                                            alignment = Alignment.Start,
                                            segmentAvatar = when {""" in src
ok_outer_asst = "if (!isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(" in src
ok_outer_user = "if (isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(" in src
ok_no_all_text = "message.parts.all { it is UIMessagePart.Text } && !message.parts.isEmptyUIMessage()" not in src
ok_no_false = "if (false && " not in src
if not (ok_user and ok_asst and ok_outer_asst and ok_outer_user and ok_no_all_text and ok_no_false):
    print(
        "[avatar] FAIL verify: user=%s assistant=%s outer_asst=%s outer_user=%s no_all_text=%s no_false=%s"
        % (ok_user, ok_asst, ok_outer_asst, ok_outer_user, ok_no_all_text, ok_no_false)
    )
    sys.exit(1)

P.write_text(src, encoding="utf-8")
print("[avatar] patched: %s" % (", ".join(changed) if changed else "nothing to do"))
print(
    "[avatar] verify OK user=%s assistant=%s outer_asst=%s outer_user=%s no_all_text=%s no_false=%s"
    % (ok_user, ok_asst, ok_outer_asst, ok_outer_user, ok_no_all_text, ok_no_false)
)
