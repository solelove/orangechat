"""用户拆分：改成真正的独立开关
- 只认 userBubbleSplitMode，不再回落到助手
- 设置页开关直接控制 NONE / 继承原模式
"""
import pathlib, sys

# ---------- 1. Assistant.kt ----------
p = pathlib.Path('app/src/main/java/me/rerere/rikkahub/data/model/Assistant.kt')
src = p.read_text(encoding='utf-8')
orig = src

old_user_field = """    // 用户气泡拆分模式：独立开关，null 表示老数据（沿用 bubbleSplitMode）
    val userBubbleSplitMode: BubbleSplitMode? = null,
    // 用户是否亲手设置过拆分开关；true 时 userBubbleSplitMode 说了算，不再跟随助手
    val userSplitModeSet: Boolean = false,"""
new_user_field = """    // 用户气泡拆分模式：null 表示老数据（沿用 bubbleSplitMode），非 null 时完全独立
    val userBubbleSplitMode: BubbleSplitMode? = null,"""
if old_user_field in src:
    src = src.replace(old_user_field, new_user_field, 1)

old_eff = """    /** 用户侧实际生效的拆分模式：亲手设过就只听自己，老数据才沿用助手 */
    val effectiveUserSplitMode: BubbleSplitMode
        get() = if (userSplitModeSet) (userBubbleSplitMode ?: BubbleSplitMode.NONE)
        else (userBubbleSplitMode ?: bubbleSplitMode)"""
new_eff = """    /** 用户侧实际生效的拆分模式：设过就完全听自己的，老数据才沿用助手 */
    val effectiveUserSplitMode: BubbleSplitMode
        get() = userBubbleSplitMode ?: bubbleSplitMode"""
if old_eff in src:
    src = src.replace(old_eff, new_eff, 1)

if src == orig:
    print('Assistant.kt: no change')
else:
    p.write_text(src, encoding='utf-8')
    print('patched Assistant.kt')

# ---------- 2. AssistantBasicPage.kt ----------
q = pathlib.Path('app/src/main/java/me/rerere/rikkahub/ui/pages/assistant/detail/AssistantBasicPage.kt')
src = q.read_text(encoding='utf-8')
orig = src

start = src.find('            // 用户气泡：单独开关，不受上面的影响')
end = src.find('        }\n \n        Card(\n            colors = CustomColors.cardColorsOnSurfaceContainer\n        ) {\n            FormItem(\n                modifier = Modifier.padding(8.dp),\n                label = {\n                    Text(stringResource(R.string.assistant_page_chat_model))')
if start == -1 or end == -1:
    print('anchor missing: start=%s end=%s' % (start, end))
    sys.exit(1)

new_block = """            // 用户气泡：独立开关，不受上面的影响
            FormItem(
                modifier = Modifier.padding(8.dp),
                label = {
                    Text("我的气泡也拆分")
                },
                description = {
                    Text("关掉就一整条不拆，只看这里，不跟助手联动")
                },
                tail = {
                    Switch(
                        checked = assistant.userBubbleSplitMode?.isEnabled == true,
                        onCheckedChange = { enabled ->
                            onUpdate(
                                assistant.copy(
                                    userBubbleSplitMode = if (enabled) BubbleSplitMode.SENTENCE
                                    else BubbleSplitMode.NONE
                                )
                            )
                        }
                    )
                }
            ) {
                if (assistant.userBubbleSplitMode?.isEnabled == true) {
                    BubbleSplitModeSelector(
                        selected = assistant.userBubbleSplitMode ?: BubbleSplitMode.SENTENCE,
                        onSelect = { selected ->
                            onUpdate(assistant.copy(userBubbleSplitMode = selected))
                        },
                    )
                }
            }

"""
src = src[:start] + new_block + src[end:]

if src == orig:
    print('AssistantBasicPage.kt: no change')
else:
    q.write_text(src, encoding='utf-8')
    print('patched AssistantBasicPage.kt')
