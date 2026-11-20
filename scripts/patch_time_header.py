#!/usr/bin/env python3
# 修复时间条不显示日期：
# 原 formatTimeHeader 里有个分支——"跟上一条同一天就只显示时分"，
# 导致跨天后的第一条（如果和它上一条同一天）也不带日期。
# 新逻辑：只有真正是今天(now)的消息才只显示时分，其余一律带日期。
import sys

PATH = "app/src/main/java/me/rerere/rikkahub/ui/pages/chat/ChatList.kt"

OLD = '''private fun formatTimeHeader(node: MessageNode, prevNode: MessageNode?): String {
    val t = node.currentMessage.createdAt
    val now = Clock.System.now().toLocalDateTime(TimeZone.currentSystemDefault())
    val hm = "%02d:%02d".format(t.hour, t.minute)
    if (t.year == now.year && t.monthNumber == now.monthNumber && t.dayOfMonth == now.dayOfMonth) {
        return hm
    }
    val prev = prevNode?.currentMessage?.createdAt
    if (prev != null && prev.year == t.year && prev.monthNumber == t.monthNumber &&
        prev.dayOfMonth == t.dayOfMonth
    ) {
        return hm
    }
    val md = "${t.monthNumber}月${t.dayOfMonth}日 $hm"
    return if (t.year == now.year) md else "${t.year}年$md"
}'''

NEW = '''private fun formatTimeHeader(node: MessageNode, prevNode: MessageNode?): String {
    val t = node.currentMessage.createdAt
    val now = Clock.System.now().toLocalDateTime(TimeZone.currentSystemDefault())
    val hm = "%02d:%02d".format(t.hour, t.minute)
    // 只有真正是今天(now)的消息才只显示时分
    if (t.year == now.year && t.monthNumber == now.monthNumber && t.dayOfMonth == now.dayOfMonth) {
        return hm
    }
    // 非今天的消息：一律带上日期
    val md = "${t.monthNumber}月${t.dayOfMonth}日 $hm"
    return if (t.year == now.year) md else "${t.year}年$md"
}'''

with open(PATH, encoding="utf-8") as f:
    src = f.read()

if NEW in src:
    print("already patched")
    sys.exit(0)

if OLD not in src:
    print("ANCHOR NOT FOUND, abort")
    sys.exit(1)

src = src.replace(OLD, NEW, 1)
with open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(src)

print("patched formatTimeHeader")
