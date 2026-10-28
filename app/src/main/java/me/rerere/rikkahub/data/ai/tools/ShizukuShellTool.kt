/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.data.ai.tools

import android.content.Context
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import me.rerere.ai.core.InputSchema
import me.rerere.ai.core.Tool
import me.rerere.ai.ui.UIMessagePart
import me.rerere.rikkahub.data.service.ShizukuShellService

/**
 * 通用 shell 工具。跑在 Shizuku 的 shell 身份下 (uid 2000)，
 * 能读别的应用数据、调用 pm/settings/dumpsys 等命令。
 * 注意：shell 不是 root，系统分区只读。
 */
fun createShizukuShellTool(@Suppress("UNUSED_PARAMETER") context: Context): Tool = Tool(
    name = "shizuku_shell",
    description = """
        Execute a shell command on the device through Shizuku, running as the shell user (uid 2000).
        Useful for: reading files under /data/data, running pm/settings/am commands,
        inspecting processes, listing files, dumpsys, etc.
        Note: this is NOT root. System partitions are read-only and some paths stay inaccessible.
        Supports pipes and redirection since the command is passed to 'sh -c'.
        Pass an explicit timeout for long-running commands; the process is killed when it expires.
        Returns exit_code, stdout, stderr, timed_out and duration_ms.
    """.trimIndent().replace("\n", " "),
    needsApproval = true,
    parameters = {
        InputSchema.Obj(
            properties = buildJsonObject {
                put("command", buildJsonObject {
                    put("type", "string")
                    put("description", "The shell command to execute. Pipes and redirection are supported.")
                })
                put("timeout_seconds", buildJsonObject {
                    put("type", "integer")
                    put("description", "Max seconds to wait before killing the process (default 20, max 120)")
                })
                put("work_dir", buildJsonObject {
                    put("type", "string")
                    put("description", "Optional working directory, e.g. /sdcard/Download")
                })
            },
            required = listOf("command")
        )
    },
    execute = { args ->
        val params = args.jsonObject
        val command = params["command"]?.jsonPrimitive?.contentOrNull
        if (command.isNullOrBlank()) {
            return@Tool listOf(UIMessagePart.Text(
                buildJsonObject {
                    put("success", false)
                    put("error", "command is required")
                }.toString()
            ))
        }

        val timeout = (params["timeout_seconds"]?.jsonPrimitive?.intOrNull ?: 20).coerceIn(1, 120)
        val workDir = params["work_dir"]?.jsonPrimitive?.contentOrNull?.takeIf { it.isNotBlank() }

        val result = ShizukuShellService.exec(
            command = command,
            timeoutSeconds = timeout.toLong(),
            workDir = workDir,
        )

        result.fold(
            onSuccess = { r ->
                listOf(UIMessagePart.Text(
                    buildJsonObject {
                        put("success", r.exitCode == 0)
                        put("exit_code", r.exitCode)
                        put("stdout", truncate(r.stdout))
                        put("stderr", truncate(r.stderr))
                        put("timed_out", r.timedOut)
                        put("duration_ms", r.durationMs)
                        put("shizuku_uid", ShizukuShellService.shizukuUid())
                    }.toString()
                ))
            },
            onFailure = { e ->
                listOf(UIMessagePart.Text(
                    buildJsonObject {
                        put("success", false)
                        put("error", e.message ?: "unknown error")
                        put("shizuku_available", ShizukuShellService.isAvailable())
                        put("permission_granted", ShizukuShellService.isPermissionGranted())
                    }.toString()
                ))
            }
        )
    }
)

private const val MAX_OUTPUT_CHARS = 12000

private fun truncate(text: String): String =
    if (text.length <= MAX_OUTPUT_CHARS) text
    else text.take(MAX_OUTPUT_CHARS) + "\n...[truncated ${text.length - MAX_OUTPUT_CHARS} chars]"
