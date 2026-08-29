package com.example.promisepocket.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey
import kotlinx.serialization.Serializable
import java.time.Instant
import java.util.UUID

@Serializable
enum class CommitmentStatus(val value: String) {
    PENDING("pending"),
    COMPLETED("completed"),
    CANCELED("canceled")
}

@Serializable
enum class AttentionReason(val value: String) {
    CLARIFICATION("clarification"),
    DUE("due"),
    BLOCKED("blocked")
}

@Serializable
@Entity(tableName = "commitments")
data class CommitmentEntity(
    @PrimaryKey
    val commitmentId: String = UUID.randomUUID().toString().replace("-", ""),
    val actorId: String,
    val summary: String,
    val rawText: String,
    val dueAt: String? = null, // ISO-8601 format e.g. "2026-08-30T12:00:00Z"
    val people: List<String> = emptyList(),
    val humanActionRequired: Boolean = true,
    val missingInformation: List<String> = emptyList(),
    val blockedReason: String? = null,
    val source: String = "chat",
    val status: CommitmentStatus = CommitmentStatus.PENDING,
    val createdAt: String = Instant.now().toString(),
    val updatedAt: String = Instant.now().toString()
) {
    val nextReviewAt: String?
        get() = if (missingInformation.isNotEmpty() || !blockedReason.isNullOrBlank()) {
            createdAt
        } else {
            dueAt
        }
}

@Serializable
data class AttentionItem(
    val commitmentId: String,
    val summary: String,
    val reason: AttentionReason,
    val prompt: String,
    val dueAt: String? = null,
    val people: List<String> = emptyList(),
    val rawText: String = "",
    val humanActionRequired: Boolean = true
)
