                if (!deviceEventContext.isNullOrBlank()) {
                    appendLine()
                    appendLine(deviceEventContext)
                }
            }

            // 每条主动消息都带统一时间上下文：真实当前时间 + 距上一条消息多久
            appendLine()
            appendLine(TimeReminderTransformer.buildReminderForProactive(lastMessageAt))
        }
    }