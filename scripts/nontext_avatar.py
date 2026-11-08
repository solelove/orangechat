#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拆分气泡模式下，图片/视频/文档段也带头像。"""
import sys

PATH = "app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessage.kt"
BUBBLE = "app/src/main/java/me/rerere/rikkahub/ui/components/message/BubbleSurface.kt"


def main() -> int:
    # 1. SegmentAvatarView 改成 internal，供 ChatMessage 用
    with open(BUBBLE, "r", encoding="utf-8") as f:
        b = f.read()
    b = b.replace(
        "@Composable\nprivate fun SegmentAvatarView(",
        "@Composable\ninternal fun SegmentAvatarView(",
        1,
    )
    with open(BUBBLE, "w", encoding="utf-8") as f:
        f.write(b)

    with open(PATH, "r", encoding="utf-8") as f:
        src = f.read()

    if "NonTextPartRow(" in src:
        print("already patched")
        return 0

    # 2. 图片段外包一层
    OLD_IMAGE = '''                    is UIMessagePart.Image -> {
                        val isImageLoading ='''
    NEW_IMAGE = '''                    is UIMessagePart.Image -> {
                        NonTextPartRow(
                            isUser = role == MessageRole.USER,
                            segmentAvatar = segmentAvatarFor(
                                isUser = role == MessageRole.USER,
                                assistant = assistant,
                                model = model,
                                userAvatar = displaySettings.userAvatar,
                                userNickname = displaySettings.userNickname,
                                showUserAvatar = displaySettings.showUserAvatar,
                                showModelIcon = displaySettings.showModelIcon,
                                showAssistantBubble = displaySettings.showAssistantBubble,
                            ),
                            avatarLoading = loading,
                        ) {
                        val isImageLoading ='''

    if OLD_IMAGE not in src:
        print("anchor: image not found", file=sys.stderr)
        return 1
    src = src.replace(OLD_IMAGE, NEW_IMAGE, 1)

    # 3. 图片段结束处补一个闭括号（原来 Image 分支结束后直接是 Document）
    OLD_SEAM = '''                        }
                    }

                    is UIMessagePart.Document -> {'''
    NEW_SEAM = '''                        }
                        }
                    }

                    is UIMessagePart.Document -> {'''
    if OLD_SEAM not in src:
        print("anchor: seam not found", file=sys.stderr)
        return 1
    src = src.replace(OLD_SEAM, NEW_SEAM, 1)

    helper = '''
/** 非文本段（图片/视频/文档）：拆分模式下跟着一个头像，保持和文字气泡对齐 */
@Composable
private fun NonTextPartRow(
    isUser: Boolean,
    segmentAvatar: SegmentAvatarSpec?,
    avatarLoading: Boolean,
    content: @Composable () -> Unit,
) {
    if (segmentAvatar == null) {
        content()
        return
    }
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top,
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        SegmentAvatarView(segmentAvatar, avatarLoading)
        Spacer(modifier = Modifier.width(8.dp))
        content()
    }
}

'''

    anchor = '@Composable\n@Suppress("UnusedCrossTarget")\ninternal fun AudioPlayerBubble'
    if anchor not in src:
        print("anchor: AudioPlayerBubble not found", file=sys.stderr)
        return 1
    src = src.replace(anchor, helper + anchor, 1)

    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)

    print("patched ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
