#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""让拆分气泡的每一段都带自己的头像（一条框一个头像）。"""
import pathlib
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/ui/components/message/BubbleSurface.kt")
src = P.read_text(encoding="utf-8")

OLD_LEFT = '''                if (segmentAvatar != null && !isRightSide) {
                    if (index == 0) {
                        SegmentAvatarView(segmentAvatar, avatarLoading)
                    } else {
                        // 后续段留白对齐，避免一堆重复头像
                        Spacer(modifier = Modifier.width(SegmentAvatarWidth))
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                }'''

NEW_LEFT = '''                if (segmentAvatar != null && !isRightSide) {
                    SegmentAvatarView(segmentAvatar, avatarLoading)
                    Spacer(modifier = Modifier.width(8.dp))
                }'''

OLD_RIGHT = '''                if (segmentAvatar != null && isRightSide) {
                    Spacer(modifier = Modifier.width(8.dp))
                    if (index == 0) {
                        SegmentAvatarView(segmentAvatar, avatarLoading)
                    } else {
                        Spacer(modifier = Modifier.width(SegmentAvatarWidth))
                    }
                }'''

NEW_RIGHT = '''                if (segmentAvatar != null && isRightSide) {
                    Spacer(modifier = Modifier.width(8.dp))
                    SegmentAvatarView(segmentAvatar, avatarLoading)
                }'''


def sub(text, old, new, tag):
    hits = text.count(old)
    if hits != 1:
        print("[fix] locate failed: %s hits=%d" % (tag, hits))
        sys.exit(1)
    print("[fix] ok %s" % tag)
    return text.replace(old, new)


src = sub(src, OLD_LEFT, NEW_LEFT, "left")
src = sub(src, OLD_RIGHT, NEW_RIGHT, "right")
P.write_text(src, encoding="utf-8")
print("[fix] done")
