"""非文本段（图片/视频/音频/文档）也带头像"""
import re, sys, pathlib

root = pathlib.Path('app/src/main/java/me/rerere/rikkahub/ui/components/message')
cm = root / 'ChatMessage.kt'
src = cm.read_text(encoding='utf-8')
orig = src

# 1) 导入 SegmentAvatarWidth
if 'import androidx.compose.foundation.layout.width\n' in src and 'SegmentAvatarWidth' not in src:
    pass

# 2) 在 MessagePartsBlock 里计算一个「非文本段头像」
anchor = """    val groupedParts = remember(parts) { parts.groupMessageParts() }
"""
if 'partAvatarSpec' not in src:
    inject = """    val groupedParts = remember(parts) { parts.groupMessageParts() }

    // 非文本段（图片/视频/音频/文档）旁边也画头像，不受拆分开关限制
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
    val partAvatarLoading = loading
"""
    src = src.replace(anchor, inject, 1)

def wrap(block_code: str, spec_indent: str = '    ') -> str:
    """把某个分支的 body 包一层带头像的行"""
    return block_code

# 3) 逐个分支外包一层 Row
def wrap_branch(marker: str, src: str, key: str) -> str:
    """
    找到 `is UIMessagePart.Xxx -> {` 对应的整个分支体，改成
    is UIMessagePart.Xxx -> { PartRow(...) { 原体 } }
    """
    idx = src.find(marker)
    if idx == -1:
        print('missing marker', marker)
        return src
    # 找分支起始的 '{' 和匹配的 '}'
    start = src.find('{', idx)
    depth = 0
    i = start
    while i < len(src):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                break
        i += 1
    end = i
    body = src[start+1:end]
    # 已经包过了就跳过
    if 'PartRow(' in body[:200]:
        return src
    new_body = '\n' + PartRow_open(role_expr=True) + body + '\n                    }'
    return src[:start+1] + new_body + src[end:]

def PartRow_open(role_expr=True) -> str:
    return """                        PartRow(
                            spec = partAvatarSpec,
                            isUser = role == MessageRole.USER,
                            loading = partAvatarLoading,
                        ) {"""

for marker in [
    'is UIMessagePart.Video ->',
    'is UIMessagePart.Audio ->',
    'is UIMessagePart.VoiceMessage ->',
    'is UIMessagePart.Image ->',
    'is UIMessagePart.Document ->',
]:
    src = wrap_branch(marker, src, marker)

# 4) 追加 PartRow 组件
if 'private fun PartRow(' not in src:
    src += """

/** 非文本段（图片/视频/文档）外框：带上头像并保证最大宽度 */
@Composable
private fun PartRow(
    spec: SegmentAvatarSpec?,
    isUser: Boolean,
    loading: Boolean,
    content: @Composable () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top,
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        if (spec != null && !isUser) {
            PartAvatarView(spec, loading)
            Spacer(modifier = Modifier.width(8.dp))
        }
        content()
        if (spec != null && isUser) {
            Spacer(modifier = Modifier.width(8.dp))
            PartAvatarView(spec, loading)
        }
    }
}

@Composable
private fun PartAvatarView(spec: SegmentAvatarSpec, loading: Boolean) {
    Box(
        modifier = Modifier.width(SegmentAvatarWidth),
        contentAlignment = Alignment.TopCenter,
    ) {
        when (spec) {
            is SegmentAvatarSpec.User -> UIAvatar(
                name = spec.nickname,
                modifier = Modifier.size(SegmentAvatarWidth),
                value = spec.avatar,
                loading = false,
            )

            is SegmentAvatarSpec.AssistantAvatar -> UIAvatar(
                name = spec.assistant.name,
                modifier = Modifier.size(SegmentAvatarWidth),
                value = spec.assistant.avatar,
                loading = loading,
            )

            is SegmentAvatarSpec.Model -> AutoAIIcon(
                name = spec.modelId,
                modifier = Modifier.size(SegmentAvatarWidth),
                loading = loading,
            )
        }
    }
}
"""

# 5) 外层不再因为「有非文本段」就画头像，避免重复
src = src.replace(
    "if (!isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false",
    "if (!isUserMessage && message.parts.all { it is UIMessagePart.Text } && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(false",
)
src = src.replace(
    "if (isUserMessage && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true",
    "if (isUserMessage && message.parts.all { it is UIMessagePart.Text } && !message.parts.isEmptyUIMessage() && !shouldHideSideAvatar(true",
)

if src == orig:
    print('no change')
    sys.exit(1)

cm.write_text(src, encoding='utf-8')
print('patched ChatMessage.kt')
