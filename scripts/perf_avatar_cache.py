#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
减少聊天卡顿：
1. AvatarFrameOverlay 的 File.exists() 每次重组都查磁盘 -> 用 remember 缓存
2. BubbleSurface 的 hasImage 依赖 imagePath，已经 remember，保持
3. SplitBubbleColumn 的 segments 已 remember，保持
"""
import pathlib
import sys

AV = pathlib.Path("app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessageAvatar.kt")
BS = pathlib.Path("app/src/main/java/me/rerere/rikkahub/ui/components/message/BubbleSurface.kt")

av = AV.read_text(encoding="utf-8")
bs = BS.read_text(encoding="utf-8")


def sub(text, old, new, tag):
    hits = text.count(old)
    if hits != 1:
        print("[perf] locate failed: %s hits=%d" % (tag, hits))
        sys.exit(1)
    print("[perf] ok %s" % tag)
    return text.replace(old, new)


# --- 1. 头像框：exists 缓存 ---
OLD_FRAME = '''    if (framePath.isNotBlank() && File(framePath).exists()) {
        val context = LocalContext.current
        val bitmap = remember(framePath) {'''

NEW_FRAME = '''    val frameExists = remember(framePath) {
        framePath.isNotBlank() && File(framePath).exists()
    }
    if (frameExists) {
        val bitmap = remember(framePath) {'''

if OLD_FRAME in av:
    av = sub(av, OLD_FRAME, NEW_FRAME, "frame exists")
else:
    print("[perf] frame already patched, skip")

# --- 2. 气泡背景图：exists 放到 remember 里（已经是，但补 layer 稳定性）---
OLD_HAS = '''    val hasImage = remember(imagePath) {
        imagePath.isNotBlank() && java.io.File(imagePath).exists()
    }'''
NEW_HAS = '''    val hasImage = remember(imagePath) {
        imagePath.isNotBlank() && runCatching { java.io.File(imagePath).exists() }.getOrDefault(false)
    }'''
if OLD_HAS in bs:
    bs = sub(bs, OLD_HAS, NEW_HAS, "bubble hasImage")

AV.write_text(av, encoding="utf-8")
BS.write_text(bs, encoding="utf-8")
print("[perf] done")
