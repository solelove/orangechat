import base64, io, sys, pathlib

P = 'app/src/main/java/me/rerere/rikkahub/ui/components/message/'

# ---------- 1. ChatMessage.kt：修 shouldHideSideAvatar 调用 ----------
p = pathlib.Path(P + 'ChatMessage.kt')
src = p.read_text(encoding='utf-8')
orig_len = len(src)

old = "!shouldHideSideAvatar(isUserMessage, assistant)"
new = ("!shouldHideSideAvatar(\n"
       "                isUser = isUserMessage,\n"
       "                showUserAvatar = settings.showUserAvatar,\n"
       "                showModelIcon = settings.showModelIcon,\n"
       "                showAssistantBubble = settings.showAssistantBubble,\n"
       "                assistant = assistant,\n"
       "            )")
if old not in src:
    print('!! ChatMessage: 找不到 shouldHideSideAvatar 调用'); sys.exit(1)
assert src.count(old) == 1, 'ChatMessage: 调用出现不止一次'
src = src.replace(old, new, 1)
p.write_text(src, encoding='utf-8')
print(f'OK ChatMessage  {orig_len} -> {len(src)}')

# ---------- 2. BubbleSurface.kt：补 PartRow ----------
q = pathlib.Path(P + 'BubbleSurface.kt')
b = q.read_text(encoding='utf-8')
b_len = len(b)

if 'fun PartRow(' in b:
    print('PartRow 已存在 跳过')
else:
    anchor = "/** 气泡外壳：宽度跟随内容，最大不超过 [maxWidth] */"
    if anchor not in b:
        print('!! BubbleSurface: 找不到锚点'); sys.exit(1)
    part_row = '''/**
 * 非文本段（图片/视频/音频/文档）外面那一行：头像 + 内容。
 * 拆分开关打开时 [spec] 才非空，否则只渲染内容，头像交给外层 ChatMessage。
 */
@Composable
internal fun PartRow(
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
            SegmentAvatarView(spec, loading)
            Spacer(modifier = Modifier.width(8.dp))
        }
        content()
        if (spec != null && isUser) {
            Spacer(modifier = Modifier.width(8.dp))
            SegmentAvatarView(spec, loading)
        }
    }
}

'''
    b = b.replace(anchor, part_row + anchor, 1)
    q.write_text(b, encoding='utf-8')
    print(f'OK BubbleSurface  {b_len} -> {len(b)}')

print('全部完成')
