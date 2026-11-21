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

P.write_text(src, encoding="utf-8")
print("[avatar] part1 done:", changed)
