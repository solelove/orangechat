#!/usr/bin/env python3
import io
import re
import sys

p = sys.argv[1]
s = io.open(p, encoding='utf-8-sig').read()

pat = re.compile(
    r'val timeReminder = if \(assistant\.enableTimeReminder\) \{\s*'
    r'TimeReminderTransformer\.buildReminder\(messages\)\s*\} else null'
)

if '时间上下文无条件注入' in s:
    print('already patched')
elif not pat.search(s):
    print('ANCHOR NOT FOUND')
    sys.exit(1)
else:
    repl = (
        '// 时间上下文无条件注入 与界面显示解耦\n'
        '            val timeReminder = TimeReminderTransformer.buildReminder(messages)'
    )
    s = pat.sub(repl, s)
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    print('patched')

for line in io.open(p, encoding='utf-8-sig').read().splitlines():
    if 'timeReminder' in line:
        print('>>', line)
