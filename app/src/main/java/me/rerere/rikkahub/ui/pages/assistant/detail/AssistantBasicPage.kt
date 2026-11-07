            HorizontalDivider()
 
            FormItem(
                modifier = Modifier.padding(8.dp),
                label = {
                    Text("消息气泡拆分")
                },
                description = {
                    Text("按句子拆分：一句话一个气泡，框跟着字走")
                },
            ) {
                BubbleSplitModeSelector(
                    selected = assistant.bubbleSplitMode,
                    onSelect = { mode ->
                        onUpdate(assistant.copy(bubbleSplitMode = mode))
                    },
                )
            }
        }
