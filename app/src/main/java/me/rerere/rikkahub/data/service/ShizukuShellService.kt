/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.data.service

import android.content.pm.PackageManager
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import rikka.shizuku.Shizuku
import java.io.ByteArrayOutputStream
import java.io.InputStream

/**
 * 通过 Shizuku 以 shell 身份执行命令。
 * GadgetbridgeService 走的是同一套 Shizuku.newProcess，这里抽成通用能力。
 */
object ShizukuShellService {

    private const val TAG = "ShizukuShellService"

    const val PERMISSION_REQUEST_CODE = 10002

    /** 单次读取流的上限，防止 cat 大文件把内存打爆 */
    private const val MAX_STREAM_BYTES = 512 * 1024

    fun isAvailable(): Boolean = try {
        Shizuku.pingBinder()
    } catch (e: Throwable) {
        Log.d(TAG, "isAvailable: ${e.message}")
        false
    }

    fun isPermissionGranted(): Boolean {
        if (!isAvailable()) return false
        return try {
            Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED
        } catch (e: Throwable) {
            Log.d(TAG, "isPermissionGranted: ${e.message}")
            false
        }
    }

    fun requestPermission() {
        try {
            if (!isAvailable() || isPermissionGranted()) return
            Shizuku.requestPermission(PERMISSION_REQUEST_CODE)
        } catch (e: Throwable) {
            Log.e(TAG, "requestPermission failed", e)
        }
    }

    fun shizukuUid(): Int = try {
        if (isAvailable()) Shizuku.getUid() else -1
    } catch (e: Throwable) {
        -1
    }

    data class ShellResult(
        val exitCode: Int,
        val stdout: String,
        val stderr: String,
        val timedOut: Boolean,
        val durationMs: Long,
    )

    suspend fun exec(
        command: String,
        timeoutSeconds: Long = 20,
        workDir: String? = null,
    ): Result<ShellResult> = withContext(Dispatchers.IO) {
        runCatching {
            if (!isAvailable()) {
                throw IllegalStateException("Shizuku is not running. Open the Shizuku app and start it first.")
            }
            if (!isPermissionGranted()) {
                throw IllegalStateException("Shizuku permission not granted. Toggle the switch again and approve the dialog.")
            }

            val started = System.currentTimeMillis()
            val process = Shizuku.newProcess(arrayOf("sh", "-c", command), null, workDir)

            val outcome = withTimeoutOrNull(timeoutSeconds * 1000L) {
                coroutineScope {
                    val outDeferred = async { process.inputStream.readLimited(MAX_STREAM_BYTES) }
                    val errDeferred = async { process.errorStream.readLimited(MAX_STREAM_BYTES) }
                    val code = withContext(Dispatchers.IO) { process.waitFor() }
                    Triple(code, outDeferred.await(), errDeferred.await())
                }
            }

            if (outcome == null) {
                try {
                    process.destroy()
                } catch (_: Throwable) {
                }
                ShellResult(
                    exitCode = -1,
                    stdout = "",
                    stderr = "command timed out after ${timeoutSeconds}s and was killed",
                    timedOut = true,
                    durationMs = System.currentTimeMillis() - started,
                )
            } else {
                ShellResult(
                    exitCode = outcome.first,
                    stdout = outcome.second,
                    stderr = outcome.third,
                    timedOut = false,
                    durationMs = System.currentTimeMillis() - started,
                )
            }
        }
    }

    private fun InputStream.readLimited(limit: Int): String {
        val buffer = ByteArrayOutputStream()
        val chunk = ByteArray(8 * 1024)
        var total = 0
        try {
            while (total < limit) {
                val read = read(chunk)
                if (read <= 0) break
                val take = minOf(read, limit - total)
                buffer.write(chunk, 0, take)
                total += take
            }
        } catch (_: Throwable) {
        }
        return buffer.toString("UTF-8")
    }
}
