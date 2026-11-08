"""修复 ChatMessage.kt 里 PartRow 包裹的收尾括号"""
import pathlib, sys, re

p = pathlib.Path('app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessage.kt')
src = p.read_text(encoding='utf-8')
orig = src

# 1) 把 "                    \n                    }}" 这种挤在一起的收尾修好
bad = re.compile(r'\n[ ]*\n[ ]*\}\}')
src = bad.sub('\n                        }\n                    }\n', src)

# 2) 统一 PartRow 内部缩进：把内容多缩进 4 格
def fix_indent(src: str) -> str:
    lines = src.split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if line.strip() == 'loading = partAvatarLoading,':
            # 下一行是 ) {，再之后到匹配收尾的内容整体 +4 缩进
            out.append(lines[i+1])  # ) {
            i += 2
            depth = 1
            indent = ' ' * 24
            while i < len(lines):
                cur = lines[i]
                stripped = cur.strip()
                if stripped == '}':
                    depth -= 1
                    if depth == 0:
                        out.append(' ' * 24 + '}')
                        i += 1
                        break
                    out.append(cur)
                elif stripped.startswith('}'):
                    out.append(cur)
                else:
                    if cur.strip():
                        if cur.startswith(indent):
                            out.append(cur)
                        else:
                            out.append(indent + cur.strip())
                    else:
                        out.append(cur)
                i += 1
            continue
        i += 1
    return '\n'.join(out)

src = fix_indent(src)

if src == orig:
    print('no change')
    sys.exit(1)

p.write_text(src, encoding='utf-8')
print('fixed ChatMessage.kt')
