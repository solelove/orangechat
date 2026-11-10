#!/usr/bin/env bash
set -euo pipefail

PM="app/src/main/java/me/rerere/rikkahub/data/service/ProactiveMessageService.kt"

# 从 77f389dc 取回原版完整文件（git 里就有）
git show 77f389dce52d53ddacce4f07ca885a2e3bcbf005:$PM > /tmp/PM.orig.kt
wc -c /tmp/PM.orig.kt

python3 - <<'PYEOF'
import io

ORIG = "/tmp/PM.orig.kt"
PM = "app/src/main/java/me/rerere/rikkahub/data/service/ProactiveMessageService.kt"

s = io.open(ORIG, encoding="utf-8").read()

def rep(s, old, new, tag):
    if old not in s:
        raise SystemExit(tag + ": ANCHOR NOT FOUND")
    if s.count(old) > 1:
        raise SystemExit(tag + ": ANCHOR AMBIGUOUS count=" + str(s.count(old)))
    return s.replace(old, new, 1)

# 1 签名加 lastMessageAt
s = rep(s,
"isFromDeviceEvent: Boolean = false, deviceEventContext: String? = null): String {",
"isFromDeviceEvent: Boolean = false, deviceEventContext: String? = null, lastMessageAt: LocalDateTime? = null): String {", "PM1")

# 2 buildString 末尾注入时间
s = rep(s,
"""                // 注入完整上下文（定位、前台app、app使用、通知、电量、健康等）
                if (!deviceEventContext.isNullOrBlank()) {
                    appendLine()
                    appendLine(deviceEventContext)
                }
            }
        }
    }""",
"""                // 注入完整上下文（定位、前台app、app使用、通知、电量、健康等）
                if (!deviceEventContext.isNullOrBlank()) {
                    appendLine()
                    appendLine(deviceEventContext)
                }
            }

            // 每条主动消息都带统一时间上下文：真实当前时间 + 距上一条消息多久
            appendLine()
            appendLine(TimeReminderTransformer.buildReminderForProactive(lastMessageAt))
        }
    }""", "PM2")

# 3 调用处传上一条消息时间
s = rep(s,
"""                val systemPrompt = buildSystemPrompt(assistant, settings, idleMinutes, proactiveSetting.jumpIdleThresholdMinutes, isFromDeviceEvent, if (isFromDeviceEvent) deviceEventContext else contextStr)""",
"""                val lastMessageAt = conversation?.messageNodes?.lastOrNull()?.messages?.lastOrNull()?.createdAt
                val systemPrompt = buildSystemPrompt(assistant, settings, idleMinutes, proactiveSetting.jumpIdleThresholdMinutes, isFromDeviceEvent, if (isFromDeviceEvent) deviceEventContext else contextStr, lastMessageAt)""", "PM3")

io.open(PM, "w", encoding="utf-8", newline="").write(s)
print("PM PATCHED bytes=" + str(len(s.encode("utf-8"))))
PYEOF

echo "===== verify ====="
wc -c "$PM"
grep -n "buildReminderForProactive" "$PM"
grep -n "lastMessageAt" "$PM"
