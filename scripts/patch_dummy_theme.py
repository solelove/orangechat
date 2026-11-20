#!/usr/bin/env python3
# 修复启动闪粉色：Settings.dummy() 的 themeId 默认取 PresetThemes[0]（樱花/粉），
# 设置未从磁盘读完前界面先用 dummy 渲染 -> 变粉；读完才切回用户主题。
# 改法：dummy() 改用中性黑("black")作为占位，不影响已保存的 themeId。
import sys

PATH = "app/src/main/java/me/rerere/rikkahub/data/datastore/PreferencesStore.kt"

OLD = """        // 构造一个用于初始化的settings, 但它不能用于保存，防止使用初始值存储
        fun dummy() = Settings(init = true)"""

NEW = """        // 构造一个用于初始化的settings, 但它不能用于保存，防止使用初始值存储
        // 启动占位主题用中性黑，避免用 PresetThemes[0]（樱花/粉）造成加载瞬间闪粉
        fun dummy() = Settings(init = true, themeId = "black")"""

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

print("patched dummy()")
