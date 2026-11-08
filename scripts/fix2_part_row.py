"""彻底修 PartRow 收尾：按行扫描重写 5 个分支"""

import pathlib, sys

p = pathlib.Path('app/src/main/java/me/rerere/rikkahub/ui/components/message/ChatMessage.kt')
lines = p.read_text(encoding='utf-8').split('\n')
orig = '\n'.join(lines)

def match_brace(lines, start_idx):
    depth = 0
    for i in range(start_idx, len(lines)):
        depth += lines[i].count('{') - lines[i].count('}')
        if depth <= 0 and i > start_idx:
            return i
    return -1

out = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.strip() == 'loading = partAvatarLoading,' and i + 1 < len(lines) and lines[i+1].strip() == ') {':
        indent = ' ' * 24
        out.append(line)
        out.append(lines[i+1])
        i += 2
        body = []
        while i < len(lines):
            s = lines[i].strip()
            # 结束条件：只包含 } 的行
            if s == '}':
                break
            body.append(lines[i])
            i += 1
        for b in body:
            out.append(b if not b.strip() else indent + b.strip())
        out.append(indent + '}')
        out.append(' ' * 20 + '}')
        # 跳过原本的 }) / }} 垃圾
        while i < len(lines) and lines[i].strip() in ('}', '}}', '})', '})}))'):
            i += 1
        continue
    out.append(line)
    i += 1

src = '\n'.join(out)

if src == orig:
    print('no change')
    sys.exit(1)

p.write_text(src, encoding='utf-8')
print('rewrote')
