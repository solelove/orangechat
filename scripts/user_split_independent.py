"""用户拆分开关独立：设过就以用户为准，不再回落到助手的模式"""
import pathlib, sys

p = pathlib.Path('app/src/main/java/me/rerere/rikkahub/data/model/Assistant.kt')
src = p.read_text(encoding='utf-8')
orig = src

old = """    // 用户气泡拆分模式：独立开关，null 表示沿用旧行为（跟随 bubbleSplitMode）
    val userBubbleSplitMode: BubbleSplitMode? = null,"""
new = """    // 用户气泡拆分模式：独立开关，null 表示老数据（沿用 bubbleSplitMode）
    val userBubbleSplitMode: BubbleSplitMode? = null,
    // 用户是否亲手设置过拆分开关；true 时 userBubbleSplitMode 说了算，不再跟随助手
    val userSplitModeSet: Boolean = false,"""
if old in src:
    src = src.replace(old, new, 1)
else:
    print('anchor1 missing')
    sys.exit(1)

old2 = """    /** 用户侧实际生效的拆分模式（未设置过就沿用旧行为） */
    val effectiveUserSplitMode: BubbleSplitMode
        get() = userBubbleSplitMode ?: bubbleSplitMode"""
new2 = """    /** 用户侧实际生效的拆分模式：亲手设过就只听自己，老数据才沿用助手 */
    val effectiveUserSplitMode: BubbleSplitMode
        get() = if (userSplitModeSet) (userBubbleSplitMode ?: BubbleSplitMode.NONE)
        else (userBubbleSplitMode ?: bubbleSplitMode)"""
if old2 in src:
    src = src.replace(old2, new2, 1)
else:
    print('anchor2 missing')
    sys.exit(1)

if src == orig:
    print('no change')
    sys.exit(1)

p.write_text(src, encoding='utf-8')
print('patched Assistant.kt')
