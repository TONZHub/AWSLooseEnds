package com.example.promisepocket.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.promisepocket.data.local.AppDatabase
import com.example.promisepocket.data.model.AttentionItem
import com.example.promisepocket.data.model.CommitmentEntity
import com.example.promisepocket.data.model.CommitmentStatus
import com.example.promisepocket.data.repository.CommitmentRepository
import com.example.promisepocket.domain.CommitmentService
import com.example.promisepocket.domain.PromiseParser
import com.example.promisepocket.domain.TimeUtils
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.temporal.ChronoUnit

enum class FilterTab {
    ALL,
    ATTENTION,
    DUE,
    COMPLETED
}

data class PromisePocketUiState(
    val currentActor: String = "local-user",
    val availableActors: List<String> = listOf("local-user", "zoe", "work-profile"),
    val filterTab: FilterTab = FilterTab.ALL,
    val searchQuery: String = "",
    val isCapturing: Boolean = false,
    val activeClarificationItem: AttentionItem? = null,
    val activeDetailCommitment: CommitmentEntity? = null,
    val userNotification: String? = null,
    val attentionItems: List<AttentionItem> = emptyList(),
    val displayedCommitments: List<CommitmentEntity> = emptyList(),
    val totalPendingCount: Int = 0,
    val totalHonoredCount: Int = 0
)

class PromisePocketViewModel(application: Application) : AndroidViewModel(application) {

    private val repository: CommitmentRepository
    val service: CommitmentService
    private val parser = PromiseParser()

    private val _currentActor = MutableStateFlow("local-user")
    private val _filterTab = MutableStateFlow(FilterTab.ALL)
    private val _searchQuery = MutableStateFlow("")
    private val _isCapturing = MutableStateFlow(false)
    private val _activeClarificationItem = MutableStateFlow<AttentionItem?>(null)
    private val _activeDetailCommitment = MutableStateFlow<CommitmentEntity?>(null)
    private val _userNotification = MutableStateFlow<String?>(null)
    private val _refreshTrigger = MutableStateFlow(0)

    private val _uiState = MutableStateFlow(PromisePocketUiState())
    val uiState: StateFlow<PromisePocketUiState> = _uiState.asStateFlow()

    init {
        val db = AppDatabase.getDatabase(application)
        repository = CommitmentRepository(db.commitmentDao())
        service = CommitmentService(repository)

        // Seed demo commitment if empty on first start
        viewModelScope.launch {
            val existing = repository.listForActor("local-user")
            if (existing.isEmpty()) {
                val now = Instant.now()
                // 1. A commitment needing clarification (date only)
                service.capture(
                    actorId = "local-user",
                    summary = "Call the dentist for Mom",
                    rawText = "I promised Mom I would call the dentist tomorrow",
                    dueAt = now.plus(1, ChronoUnit.DAYS).toString(),
                    people = listOf("Mom"),
                    humanActionRequired = true,
                    missingInformation = emptyList()
                )
                // 2. An exact promise with clock time
                service.capture(
                    actorId = "local-user",
                    summary = "Send quarterly review report",
                    rawText = "Send quarterly review report by Friday at 2pm",
                    dueAt = now.plus(2, ChronoUnit.DAYS).toString(),
                    people = listOf("Team"),
                    humanActionRequired = true,
                    missingInformation = emptyList()
                )
            }
            refreshData()
        }
    }

    private fun refreshData() {
        viewModelScope.launch {
            val actor = _currentActor.value
            val tab = _filterTab.value
            val query = _searchQuery.value
            val capturing = _isCapturing.value
            val clarifyItem = _activeClarificationItem.value
            val detailItem = _activeDetailCommitment.value
            val notification = _userNotification.value

            val commitments = repository.listForActor(actor)
            val attention = service.review(actor, commitments)

            val filtered = commitments.filter { item ->
                val matchesQuery = query.isBlank() ||
                        item.summary.contains(query, ignoreCase = true) ||
                        item.rawText.contains(query, ignoreCase = true) ||
                        item.people.any { p -> p.contains(query, ignoreCase = true) }

                val matchesTab = when (tab) {
                    FilterTab.ALL -> item.status == CommitmentStatus.PENDING
                    FilterTab.ATTENTION -> attention.any { it.commitmentId == item.commitmentId }
                    FilterTab.DUE -> {
                        item.status == CommitmentStatus.PENDING &&
                                item.dueAt != null &&
                                TimeUtils.parseInstant(item.dueAt)?.let { !it.isAfter(Instant.now()) } == true
                    }
                    FilterTab.COMPLETED -> item.status == CommitmentStatus.COMPLETED
                }

                matchesQuery && matchesTab
            }

            _uiState.value = PromisePocketUiState(
                currentActor = actor,
                filterTab = tab,
                searchQuery = query,
                isCapturing = capturing,
                activeClarificationItem = clarifyItem,
                activeDetailCommitment = detailItem,
                userNotification = notification,
                attentionItems = attention,
                displayedCommitments = filtered,
                totalPendingCount = commitments.count { it.status == CommitmentStatus.PENDING },
                totalHonoredCount = commitments.count { it.status == CommitmentStatus.COMPLETED }
            )
        }
    }

    fun setActor(actor: String) {
        _currentActor.value = actor
        refreshData()
    }

    fun setFilterTab(tab: FilterTab) {
        _filterTab.value = tab
        refreshData()
    }

    fun setSearchQuery(query: String) {
        _searchQuery.value = query
        refreshData()
    }

    fun openClarification(item: AttentionItem) {
        _activeClarificationItem.value = item
        refreshData()
    }

    fun closeClarification() {
        _activeClarificationItem.value = null
        refreshData()
    }

    fun openDetail(commitmentId: String) {
        viewModelScope.launch {
            val item = repository.getCommitment(_currentActor.value, commitmentId)
            _activeDetailCommitment.value = item
            refreshData()
        }
    }

    fun closeDetail() {
        _activeDetailCommitment.value = null
        refreshData()
    }

    fun dismissNotification() {
        _userNotification.value = null
        refreshData()
    }

    fun capturePromise(rawText: String) {
        viewModelScope.launch {
            _isCapturing.value = true
            refreshData()
            try {
                val parsed = parser.parseUserUtterance(rawText)
                val commitment = service.capture(
                    actorId = _currentActor.value,
                    summary = parsed.summary,
                    rawText = rawText,
                    dueAt = parsed.dueAt,
                    people = parsed.people,
                    humanActionRequired = parsed.humanActionRequired,
                    missingInformation = parsed.missingInformation
                )
                _userNotification.value = "Promise kept: \"${commitment.summary}\""
            } catch (e: Exception) {
                _userNotification.value = "Error capturing promise: ${e.message}"
            } finally {
                _isCapturing.value = false
                refreshData()
            }
        }
    }

    fun clarifyTime(answer: String, resolvedDueAtIso: String) {
        val activeItem = _activeClarificationItem.value ?: return
        viewModelScope.launch {
            try {
                service.clarifyTime(
                    actorId = _currentActor.value,
                    commitmentId = activeItem.commitmentId,
                    answer = answer,
                    dueAt = resolvedDueAtIso
                )
                _activeClarificationItem.value = null
                _userNotification.value = "Exact time saved."
            } catch (e: Exception) {
                _userNotification.value = "Error updating time: ${e.message}"
            } finally {
                refreshData()
            }
        }
    }

    fun setStatus(commitmentId: String, status: CommitmentStatus) {
        viewModelScope.launch {
            try {
                service.markStatus(_currentActor.value, commitmentId, status)
                _activeDetailCommitment.value = repository.getCommitment(_currentActor.value, commitmentId)
            } catch (e: Exception) {
                _userNotification.value = "Error updating status: ${e.message}"
            } finally {
                refreshData()
            }
        }
    }

    fun setBlockedReason(commitmentId: String, reason: String?) {
        viewModelScope.launch {
            try {
                service.setBlockedReason(_currentActor.value, commitmentId, reason)
                _activeDetailCommitment.value = repository.getCommitment(_currentActor.value, commitmentId)
            } catch (e: Exception) {
                _userNotification.value = "Error updating blocker: ${e.message}"
            } finally {
                refreshData()
            }
        }
    }

    fun deleteCommitment(commitmentId: String) {
        viewModelScope.launch {
            try {
                repository.deleteById(_currentActor.value, commitmentId)
                _activeDetailCommitment.value = null
                _userNotification.value = "Commitment deleted."
            } catch (e: Exception) {
                _userNotification.value = "Error deleting: ${e.message}"
            } finally {
                refreshData()
            }
        }
    }
}
