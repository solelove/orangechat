#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「参考历史聊天记录」从 system 里挪出来，改成一条单独的历史消息。

为什么（2026-11-26 实测结论）：
  请求结构是 messages[0]=静态system, messages[1]=动态system, 后面是对话历史, 最后是 tools。
  实测 106.5K 总量只有 28.9K 命中，那个 28.9K 正好等于前两条 system 的长度。
  也就是说：缓存比到动态段就断了，后面 106 条历史 + 166 个工具全部吃不到。

  断点来源只有一个：GenerationPrompts.kt 里的 buildRecentChatsPrompt
      put("last_chat", conversation.updateAt.toLocalDate())
  每轮你刚发完消息，当前会话的 updateAt 就是今天，日期一变、
  10 条列表的排序内容也跟着变。它每轮必然不同，稳稳卡在动态段中间。

  外置记忆库是「未配置」，代码走不到检索分支，排除。
  时间提醒已经由 patch_time_tail 挪到列表末尾，排除。

做法（不动内容的性质，只换位置）：
  - 动态 system 里删掉 buildRecentChatsPrompt
  - 在对话历史之后、时间提醒之前，单独 add 一条 assistant 消息，
    用 <recent_chats> 标签包起来，明确是「参考存档」而不是「现在正在说的话」，
    避免模型把旧聊天当成当前轮次。

  排序变成：静态system(不变) -> 动态system(记忆+工具, 十几天一变) -> 历史 -> 最近会话(每轮变) -> 时间(每分钟变)
  越往后越爱变，前缀能命中的长度就越长。

必须跑在 patch_prompt_two_system.py 和 patch_time_tail.py 之后。

安全设计：锚点唯一性断言、命中数断言、结构断言、括号平衡，任一不过不落盘。
"""
import pathlib
import re
import sys

P = pathlib.Path("app/src/main/java/me/rerere/rikkahub/data/ai/GenerationHandler.kt")
MARK = "// [recent-tail]"

if not P.exists():
    print("[recent] FAIL: GenerationHandler.kt not found")
    sys.exit(1)

text = P.read_text(encoding="utf-8")

if MARK in text:
    print("[recent] already patched, skip")
    sys.exit(0)

# ---------- 1. 从动态 system 里摘掉最近会话 ----------
DYN_RECENT = (
    "                if (assistant.enableRecentChatsReference) {\n"
    "                    appendLine()\n"
    "                    append(buildRecentChatsPrompt(assistant, conversationRepo))\n"
    "                }\n"
)

if text.count(DYN_RECENT) != 1:
    print("[recent] FAIL: dynamic recent-chats block hits=%d" % text.count(DYN_RECENT))
    sys.exit(1)

text = text.replace(DYN_RECENT, "                // [recent-tail] 最近会话已移出 system，改放历史之后单独一条\n", 1)

# ---------- 2. 在时间提醒之前插入独立的一条 ----------
TAIL_ANCHOR = "            if (!timeReminder.isNullOrBlank()) {\n                add(UIMessage.user(timeReminder))\n            }\n"
if text.count(TAIL_ANCHOR) != 1:
    print("[recent] FAIL: time-tail anchor hits=%d" % text.count(TAIL_ANCHOR))
    sys.exit(1)

INSERT = (
    "            // [recent-tail] 参考历史聊天记录：单独一条 assistant 消息，不进 system。\n"
    "            // 原因：它带 last_chat 日期，每轮都会变，放在 system 里会把后面全部历史切碎。\n"
    "            // 用标签包住，明确是存档参考，不是当前轮次正在说的话。\n"
    "            if (assistant.enableRecentChatsReference) {\n"
    "                val recentChatsBlock = buildRecentChatsPrompt(assistant, conversationRepo)\n"
    "                if (recentChatsBlock.isNotBlank()) {\n"
    "                    add(UIMessage.assistant(\"<recent_chats>\\n\" + recentChatsBlock.trim() + \"\\n</recent_chats>\"))\n"
    "                }\n"
    "            }\n"
)

text = text.replace(TAIL_ANCHOR, INSERT + TAIL_ANCHOR, 1)

# ---------- 3. 校验 ----------
dyn_start = text.find("val dynamicSystem = buildString {")
dyn_end = text.find("add(UIMessage.system(prompt = dynamicSystem))")

checks = {
    "mark": MARK in text,
    "dyn_found": dyn_start > 0 and dyn_end > dyn_start,
    "recent_out_of_system": "buildRecentChatsPrompt" not in text[dyn_start:dyn_end],
    "memory_still_in_system": "buildMemoryPrompt" in text[dyn_start:dyn_end],
    "tools_still_in_system": "tools.forEach" in text[dyn_start:dyn_end],
    "recent_call_kept": text.count("buildRecentChatsPrompt(assistant, conversationRepo)") == 1,
    "wrapped_block": "<recent_chats>" in text and "</recent_chats>" in text,
    "static_alive": "val staticSystem = buildString {" in text,
    "time_tail_alive": "add(UIMessage.user(timeReminder))" in text,
    "limit_intact": text.count("addAll(messages.limitContext(assistant.contextMessageSize))") == 1,
    "translate_alive": "fun translateText(" in text,
    "generate_alive": "fun generateText(" in text,
    "codeblock_alive": "private fun buildCodeBlockPrompt()" in text,
    "brace_balance": text.count("{") == text.count("}"),
}

i_recent = text.find("<recent_chats>")
i_tail = text.find("add(UIMessage.user(timeReminder))")
i_lim = text.find("addAll(messages.limitContext(assistant.contextMessageSize))")
checks["order_ok"] = 0 < i_lim < i_recent < i_tail

for k in checks:
    print("[recent] %-24s %s" % (k, "OK" if checks[k] else "FAIL"))

if not all(checks.values()):
    print("[recent] ABORT: 校验未通过，未写入文件")
    sys.exit(1)

P.write_text(text, encoding="utf-8", newline="")
print("[recent] patched OK (%d bytes)" % len(text))
