"""修 ChatMessage.kt：PartRow 包裹后的收尾括号"""
import pathlib, sys, re

p = pathlib.Path('app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessage.kt')
src = p.read_text(encoding='utf-8')
orig = src

# 收尾写成 "                    \n                    }}" 的地方，改成正确的两层收尾
src = re.sub(
    r'\n[ ]*\n[ ]*\}\}',
    '\n                        }\n                    }',
    src,
)

# 顺手让 PartRow 里的内容缩进对齐（只处理紧跟 ") {" 之后、到收尾之间的行）
lines = src.split('\n')
out = []
i = 0
while i < len(lines):
    out.append(lines[i])
    if lines[i].strip() == 'loading = partAvatarLoading,':
        if i + 1 < len(lines):
            out.append(lines[i + 1])  # ) {
        i += 2
        while i < len(lines):
            cur = lines[i]
            s = cur.strip()
            if s == '}' and cur.startswith(' ' * 24) and not cur.startswith(' ' * 28):
                out.append(cur)
                i += 1
                break
            if not s:
                out.append(cur)
            elif s.startswith('}'):
                out.append(cur)
            else:
                out.append(' ' * 28 + s)
            i += 1
        continue
    i += 1

src = '\n'.join(out)

if src == orig:
    print('no change')
    sys.exit(1)

p.write_text(src, encoding='utf-8')
print('fixed')
