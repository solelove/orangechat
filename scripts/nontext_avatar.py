#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拆分气泡模式下，图片/视频/文档段也带头像。"""
import sys

PATH = "app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessage.kt"

OLD_IMAGE = """                    is UIMessagePart.Image -> {
                        val isImageLoading =
                            part.url.isBlank() || part.url.matches(Regex("^data:image/[^;]*;base64,\\\\s*$"))
                        if (isImageLoading) {"""

NEW_IMAGE = """                    is UIMessagePart.Image -> {
                        val isImageLoading =
                            part.url.isBlank() || part.url.matches(Regex("^data:image/[^;]*;base64,\\\\s*$"))
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
                        if (isImageLoading) {"""

OLD_DOC_END = """                                }
                            }
                        }
                    }

                    is UIMessagePart.Document -> {"""

NEW_DOC_END = """                                }
                            }
                        }
                        }
                    }

                    is UIMessagePart.Document -> {"""


def main() -> int:
    with open(PATH, "r", encoding="utf-8") as f:
        src = f.read()

    if "NonTextPartRow(" in src:
        print("already patched")
        return 0

    if OLD_IMAGE not in src:
        print("anchor: image not found", file=sys.stderr)
        return 1

    src = src.replace(OLD_IMAGE, NEW_IMAGE, 1)

    if OLD_DOC_END not in src:
        print("anchor: image tail not found", file=sys.stderr)
        return 1

    src = src.replace(OLD_DOC_END, NEW_DOC_END, 1)

    # 关闭文档段前的括号补齐：Document 分支结束处补一个右括号
    OLD_TAIL = """                    else -> {
                        // 跳过未知类型
                    }"""
    NEW_TAIL = """                    }
                    else -> {
                        // 跳过未知类型
                    }"""
    if OLD_TAIL in src:
        src = src.replace(OLD_TAIL, NEW_TAIL, 1)

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
        if (segmentAvatar != null && !isUser) {
            SegmentAvatarView(segmentAvatar, avatarLoading)
            Spacer(modifier = Modifier.width(8.dp))
        }
        content()
        if (segmentAvatar != null && isUser) {
            Spacer(modifier = Modifier.width(8.dp))
            SegmentAvatarView(segmentAvatar, avatarLoading)
        }
    }
}
'''

    anchor = "@Composable\n@Suppress(\"UnusedCrossTarget\")\ninternal fun AudioPlayerBubble"
    if anchor not in src:
        print("anchor: AudioPlayerBubble not found", file=sys.stderr)
        return 1
    src = src.replace(anchor, helper + "\n" + anchor, 1)

    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)

    print("patched ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
