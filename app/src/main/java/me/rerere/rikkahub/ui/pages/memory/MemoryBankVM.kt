/*
 * 橘瓣 OrangeChat
 * 衍生自 RikkaHub (https://github.com/rikkahub/rikkahub)，原作者 RE
 * 本项目基于 GNU AGPL v3 开源，详见根目录 LICENSE 文件
 */

package me.rerere.rikkahub.ui.pages.memory

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import me.rerere.rikkahub.data.db.entity.MemoryBankEntity
import me.rerere.rikkahub.data.service.MemoryBankService
import me.rerere.rikkahub.plugin.manager.PluginManager

data class PendingMemory(
    val id: String,
    val title: String,
    val content: String,
    val tags: List<String>,
    val ts: Long,
)

class MemoryBankVM(
    private val memoryBankService: MemoryBankService,
    private val pluginManager: PluginManager,
) : ViewModel() {

    companion object {
        const val PENDING_PLUGIN_ID = "com.solelove.memorypal"
    }

    private val _memories = MutableStateFlow<List<MemoryBankEntity>>(emptyList())
    val memories: StateFlow<List<MemoryBankEntity>> = _memories.asStateFlow()

    private val _todayPhaseSummaries = MutableStateFlow<List<MemoryBankEntity>>(emptyList())
    val todayPhaseSummaries: StateFlow<List<MemoryBankEntity>> = _todayPhaseSummaries.asStateFlow()

    private val _dailySummaries = MutableStateFlow<List<MemoryBankEntity>>(emptyList())
    val dailySummaries: StateFlow<List<MemoryBankEntity>> = _dailySummaries.asStateFlow()

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _selectedType = MutableStateFlow("")
    val selectedType: StateFlow<String> = _selectedType.asStateFlow()

    private val _selectedAssistantId = MutableStateFlow<String?>(null)
    val selectedAssistantId: StateFlow<String?> = _selectedAssistantId.asStateFlow()

    private val _assistantIds = MutableStateFlow<List<String>>(emptyList())
    val assistantIds: StateFlow<List<String>> = _assistantIds.asStateFlow()

    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading.asStateFlow()

    private val _stats = MutableStateFlow(MemoryBankService.MemoryStats())
    val stats: StateFlow<MemoryBankService.MemoryStats> = _stats.asStateFlow()

    private val _pendingMemories = MutableStateFlow<List<PendingMemory>>(emptyList())
    val pendingMemories: StateFlow<List<PendingMemory>> = _pendingMemories.asStateFlow()

    private val _pendingBusy = MutableStateFlow<String?>(null)
    val pendingBusy: StateFlow<String?> = _pendingBusy.asStateFlow()

    private val _pendingMessage = MutableStateFlow<String?>(null)
    val pendingMessage: StateFlow<String?> = _pendingMessage.asStateFlow()

    private val _pendingPluginAvailable = MutableStateFlow(true)
    val pendingPluginAvailable: StateFlow<Boolean> = _pendingPluginAvailable.asStateFlow()

    init {
        loadMemories()
        loadPending()
    }

    fun loadMemories() {
        viewModelScope.launch {
            _loading.value = true
            try {
                _assistantIds.value = memoryBankService.getAssistantIds()
                _stats.value = memoryBankService.getStats(_selectedAssistantId.value)
                val selectedType = _selectedType.value
                val assistantId = _selectedAssistantId.value
                if (selectedType.isEmpty()) {
                    _todayPhaseSummaries.value = memoryBankService.getTodayPhaseSummaries(assistantId)
                    _dailySummaries.value = memoryBankService.getDailySummaries(assistantId)
                    _memories.value = emptyList()
                } else {
                    _memories.value = memoryBankService.searchMemories(
                        keyword = _searchQuery.value,
                        type = selectedType,
                        limit = 100,
                        assistantId = assistantId,
                    )
                    _todayPhaseSummaries.value = emptyList()
                    _dailySummaries.value = emptyList()
                }
            } finally {
                _loading.value = false
            }
        }
    }

    private suspend fun callPendingTool(tool: String, args: Map<String, String> = emptyMap()): JsonObject? {
        val params: JsonObject = buildJsonObject {
            args.forEach { (k, v) -> put(k, JsonPrimitive(v)) }
        }
        val result = pluginManager.callTool(PENDING_PLUGIN_ID, tool, params)
        return result.getOrNull()?.let { el -> runCatching { el.jsonObject }.getOrNull() }
    }

    fun loadPending() {
        viewModelScope.launch {
            try {
                val obj = callPendingTool("memory_pending_list")
                if (obj == null) {
                    _pendingPluginAvailable.value = false
                    return@launch
                }
                _pendingPluginAvailable.value = true
                val items = obj["items"]?.jsonArray
                val list = mutableListOf<PendingMemory>()
                items?.forEach { el ->
                    runCatching {
                        val o = el.jsonObject
                        val tags = o["tags"]?.jsonArray?.mapNotNull { it.jsonPrimitive.contentOrNull } ?: emptyList()
                        list.add(
                            PendingMemory(
                                id = o["id"]?.jsonPrimitive?.contentOrNull ?: "",
                                title = o["title"]?.jsonPrimitive?.contentOrNull ?: "",
                                content = o["content"]?.jsonPrimitive?.contentOrNull ?: "",
                                tags = tags,
                                ts = o["ts"]?.jsonPrimitive?.contentOrNull?.toLongOrNull() ?: 0L,
                            )
                        )
                    }
                }
                _pendingMemories.value = list
            } catch (e: Exception) {
                _pendingPluginAvailable.value = false
            }
        }
    }

    fun acceptPending(item: PendingMemory, editedContent: String?) {
        viewModelScope.launch {
            _pendingBusy.value = item.id
            try {
                val args = mutableMapOf("id" to item.id)
                if (!editedContent.isNullOrBlank()) args["content"] = editedContent
                val obj = callPendingTool("memory_pending_accept", args)
                val ok = obj?.get("success")?.jsonPrimitive?.contentOrNull == "true"
                _pendingMessage.value = if (ok) "已存进记忆库" else "存入失败"
                loadPending()
                loadMemories()
            } finally {
                _pendingBusy.value = null
            }
        }
    }

    fun dropPending(item: PendingMemory) {
        viewModelScope.launch {
            _pendingBusy.value = item.id
            try {
                val obj = callPendingTool("memory_pending_drop", mapOf("id" to item.id))
                val ok = obj?.get("success")?.jsonPrimitive?.contentOrNull == "true"
                _pendingMessage.value = if (ok) "已丢掉" else "丢弃失败"
                loadPending()
            } finally {
                _pendingBusy.value = null
            }
        }
    }

    fun summarizeNow() {
        viewModelScope.launch {
            _pendingBusy.value = "__summarize__"
            try {
                val obj = callPendingTool("memory_summarize_now")
                val ok = obj?.get("success")?.jsonPrimitive?.contentOrNull == "true"
                _pendingMessage.value = if (ok) "已总结" else "总结失败"
                loadPending()
            } finally {
                _pendingBusy.value = null
            }
        }
    }

    fun clearPendingMessage() {
        _pendingMessage.value = null
    }

    fun setSearchQuery(query: String) {
        _searchQuery.value = query
        loadMemories()
    }

    fun setSelectedType(type: String) {
        _selectedType.value = type
        loadMemories()
    }

    fun setSelectedAssistantId(assistantId: String?) {
        _selectedAssistantId.value = assistantId
        loadMemories()
    }

    fun deleteMemory(id: Int) {
        viewModelScope.launch {
            memoryBankService.deleteMemory(id)
            loadMemories()
        }
    }

    fun rebuildIndex() {
        viewModelScope.launch {
            _loading.value = true
            try {
                memoryBankService.rebuildIndex()
                loadMemories()
            } finally {
                _loading.value = false
            }
        }
    }

    fun processPendingVectors() {
        viewModelScope.launch {
            _loading.value = true
            try {
                memoryBankService.processPendingVectors()
                loadMemories()
            } finally {
                _loading.value = false
            }
        }
    }
}
