#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2.2.3 基线（7b041d77）上的 BubbleSurface.kt：v12.1

问题：SplitBubbleColumn 在 mode.isEnabled == false 时直接 BubbleSurface + return，
      完全没碰 segmentAvatar。所以不开拆分时气泡旁边没有头像（用户 2026-11-21 实测）。

改法：把 early-return 那个分支也包进 Row，按 alignment 决定头像在左还是右。
      开拆分的那条路完全不动。
"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/ui/components/message/BubbleSurface.kt")
src = P.read_text(encoding="utf-8")

OLD = """    if (!mode.isEnabled) {
        BubbleSurface(
            imagePath = imagePath,
            cornerRadius = cornerRadius,
            color = color,
            overlayEnabled = overlayEnabled,
            bubbleAlpha = bubbleAlpha,
            maxWidth = maxWidth,
            animate = true,
            onClick = onClick,
        ) {
            content(text)
        }
        return
    }
"""

NEW = """    if (!mode.isEnabled) {
        // 不开拆分也要带头像：整条气泡一个头像，按对齐方向放在左/右侧
        val singleRightSide = alignment == Alignment.End
        val singleAvatarSpace = if (segmentAvatar != null) SegmentAvatarWidth + 8.dp else 0.dp
        val singleMaxWidth = (maxWidth - singleAvatarSpace).coerceAtLeast(120.dp)
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.Top,
            horizontalArrangement = if (singleRightSide) Arrangement.End else Arrangement.Start,
        ) {
            if (segmentAvatar != null && !singleRightSide) {
                SegmentAvatarView(segmentAvatar, avatarLoading)
                Spacer(modifier = Modifier.width(8.dp))
            }
            BubbleSurface(
                imagePath = imagePath,
                cornerRadius = cornerRadius,
                color = color,
                overlayEnabled = overlayEnabled,
                bubbleAlpha = bubbleAlpha,
                maxWidth = singleMaxWidth,
                animate = true,
                onClick = onClick,
            ) {
                content(text)
            }
            if (segmentAvatar != null && singleRightSide) {
                Spacer(modifier = Modifier.width(8.dp))
                SegmentAvatarView(segmentAvatar, avatarLoading)
            }
        }
        return
    }
"""


def apply(old, new, tag):
    global src
    if old in src:
        if src.count(old) != 1:
            print("[bubble] FAIL %s: anchor hits=%d" % (tag, src.count(old)))
            sys.exit(1)
        src = src.replace(old, new, 1)
        print("[bubble] patched %s" % tag)
        return
    if new in src:
        print("[bubble] %s already patched" % tag)
        return
    print("[bubble] FAIL %s: anchor not found" % tag)
    sys.exit(1)


apply(OLD, NEW, "single-avatar")

P.write_text(src, encoding="utf-8")

checks = {
    "early_return_wrapped": "// 不开拆分也要带头像" in src,
    "uses_segment_avatar_in_single": "SegmentAvatarView(segmentAvatar, avatarLoading)\n                Spacer(modifier = Modifier.width(8.dp))" in src,
    "still_returns": "        return\n    }\n\n    // 只在文本或模式变化时重新切分" in src,
    "split_path_intact": "val segments = remember(text, mode) { splitByMode(text, mode) }" in src,
    "avatar_space_intact": "val avatarSpace = if (segmentAvatar != null) SegmentAvatarWidth + 8.dp else 0.dp" in src,
    "bubble_surface_intact": "fun BubbleSurface(" in src,
    "segment_avatar_view_intact": "private fun SegmentAvatarView(spec: SegmentAvatarSpec, loading: Boolean)" in src,
}
fails = [k for k, v in checks.items() if not v]
if fails:
    print("[bubble] FAIL verify:", ", ".join(fails))
    sys.exit(1)
print("[bubble] verify OK")
