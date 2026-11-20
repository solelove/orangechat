#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 v2.2.3 基线（7b041d77）上修正头像排布（v7）。

目标形态（微信式，一条消息只一个头像，永远跟内容顶对齐）：
  - 不拆分气泡：外层画一个侧边头像，整条消息（文字+图片混排）共用这一个
  - 拆分气泡：外层不画，每个小气泡自己贴身像

v6 的失败：
  ChatMessage.kt 里 sideAvatarVisible 保留了基线那句
  `message.parts.all { it is UIMessagePart.Text }`，
  所以一混图片外层就让位；同时内层的 textSegmentAvatar / partAvatarSpec
  在「混合消息」时也各带一个，两个头像各自跟自己的行高走，错开半个身位。

v7 做法：
  1) 外层 sideAvatarVisible 只留 isEmptyUIMessage + shouldHideSideAvatar
  2) 文本段 / 非文本段的头像只在「真拆分」时给（hasNonText 不再参与）
  3) SplitBubbleColumn / PartRow 的 spec 保留，拆分时照常逐段画

判定方式：先归一化，再校验。所有历史形态都能收敛到同一结果。
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
    print("[avatar] %s: anchor absent, nothing to do" % tag)
    return False


# ==== 1) 外层侧边头像：去掉 v6 写的 sideAvatarVisible 组合，改成只认拆分状态 ====
# v6 现在的形态
v6_outer = """    // 只有纯文本且没开拆分 才由外层画那唯一一个头像
    val sideAvatarVisible = remember(message.parts, assistant) {
        message.parts.all { it is UIMessagePart.Text } &&
            !message.parts.isEmptyUIMessage() &&
            !shouldHideSideAvatar(isUserMessage, assistant)
    }"""
v7_outer = """    // 一条消息只画一个侧边头像：不拆分时由外层画，拆分时让位给小气泡
    val sideAvatarVisible = remember(message.parts, assistant) {
        !message.parts.isEmptyUIMessage() &&
            !shouldHideSideAvatar(isUserMessage, assistant)
    }"""

if not patch(v6_outer, v7_outer, "outer-side", required=False):
    # 万一 v6 的注释没写进去，退化到只替换表达式体
    patch(
        """        message.parts.all { it is UIMessagePart.Text } &&
            !message.parts.isEmptyUIMessage() &&
            !shouldHideSideAvatar(isUserMessage, assistant)""",
        """        !message.parts.isEmptyUIMessage() &&
            !shouldHideSideAvatar(isUserMessage, assistant)""",
        "outer-side-body",
        required=False,
    )

# ==== 2) 文本段头像：hasNonText 不再参与（混合消息也交给外层那个）====
patch(
    """    // 这条消息里有没有非文本段（图片/视频/音频/文档/工具）
    val hasNonText = remember(parts) { parts.any { it !is UIMessagePart.Text } }

""",
    "",
    "drop-hasNonText",
    required=False,
)

# v6 里 textSegmentAvatar 的 splitOrMixed 参数
patch(
    """            splitOrMixed = willSplitIntoBubbles(isUser, assistant) || hasNonText,
""",
    """            splitOrMixed = willSplitIntoBubbles(isUser, assistant),
""",
    "text-seg-split-only",
    required=False,
)

# 万一 v6 用的是别的方式引用 hasNonText，兜底把它整体清掉
if "hasNonText" in src:
    print("[avatar] WARN: hasNonText still referenced, forcing cleanup")
    src = src.replace(
        "            splitOrMixed = willSplitIntoBubbles(isUser, assistant) || hasNonText,",
        "            splitOrMixed = willSplitIntoBubbles(isUser, assistant),",
    )

# ==== 3) 非文本段头像：同样只在拆分时给 ====
# v6 的写法是把 hasNonText 也并进判断，这里统一收回到 willSplitIntoBubbles
patch(
    """            showModelIcon = displaySettings.showModelIcon,
            splitOrMixed = willSplitIntoBubbles(isUser, assistant) || hasNonText,
        )
    }

    // 图片/视频/音频/文档 旁边的头像 不受拆分开关影响""",
    """            showModelIcon = displaySettings.showModelIcon,
            splitOrMixed = willSplitIntoBubbles(isUser, assistant),
        )
    }

    // 图片/视频/音频/文档 旁边的头像 拆分时自己带""",
    "part-seg-split-only",
    required=False,
)

P.write_text(src, encoding="utf-8")

# ==== 校验 ====
ok_no_all_text = "message.parts.all { it is UIMessagePart.Text } &&" not in src
ok_no_false = "if (false && " not in src
ok_outer = "!message.parts.isEmptyUIMessage() &&\n            !shouldHideSideAvatar(isUserMessage, assistant)" in src
ok_no_mixed = "|| hasNonText" not in src
ok_user_seg = "segmentAvatar = if (displaySettings.showUserAvatar)" in src
ok_asst_seg = "SegmentAvatarSpec.Model(model.modelId)" in src
ok_partrow = "PartRow(partAvatarSpec, isUser, loading)" in src

fails = []
for name, v in [
    ("no_all_text", ok_no_all_text),
    ("no_false", ok_no_false),
    ("outer_ok", ok_outer),
    ("no_mixed_avatar", ok_no_mixed),
    ("user_seg", ok_user_seg),
    ("assistant_seg", ok_asst_seg),
    ("partrow", ok_partrow),
]:
    if not v:
        fails.append(name)

print("[avatar] changed: %s" % (", ".join(changed) if changed else "nothing"))
if fails:
    print("[avatar] FAIL verify: %s" % ", ".join(fails))
    sys.exit(1)
print("[avatar] verify OK")
