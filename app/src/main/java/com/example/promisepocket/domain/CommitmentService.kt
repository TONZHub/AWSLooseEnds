package com.example.promisepocket.domain

import com.example.promisepocket.data.model.AttentionItem
import com.example.promisepocket.data.model.AttentionReason
import com.example.promisepocket.data.model.CommitmentEntity
import com.example.promisepocket.data.model.CommitmentStatus
import com.example.promisepocket.data.repository.CommitmentRepository
import java.time.Instant
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.UUID

object TimeUtils {
    private val REGEX_NOON_MIDNIGHT = Regex("""\b(?:noon|midnight)\b""", RegexOption.IGNORE_CASE)
    private val REGEX_AM_PM = Regex("""\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\b""", RegexOption.IGNORE_CASE)
    private val REGEX_24HR = Regex("""\b(?:[01]?\d|2[0-3]):[0-5]\d\b""")
    private val REGEX_AT_TIME = Regex("""\bat\s+\d{1,2}(?::\d{2})?\b""", RegexOption.IGNORE_CASE)

    fun hasExplicitClockTime(text: String): Boolean {
        return REGEX_NOON_MIDNIGHT.containsMatchIn(text) ||
                REGEX_AM_PM.containsMatchIn(text) ||
                REGEX_24HR.containsMatchIn(text) ||
                REGEX_AT_TIME.containsMatchIn(text)
    }

    fun parseInstant(isoString: String?): Instant? {
        if (isoString.isNullOrBlank()) return null
        return try {
            Instant.parse(isoString)
        } catch (e: Exception) {
            try {
                OffsetDateTime.parse(isoString).toInstant()
            } catch (e2: Exception) {
                null
            }
        }
    }

    fun formatDisplayDate(isoString: String?): String {
        val instant = parseInstant(isoString) ?: return "No time set"
        val zone = java.time.ZoneId.systemDefault()
        val zdt = instant.atZone(zone)
        val formatter = DateTimeFormatter.ofPattern("EEE, MMM d • h:mm a")
        return formatter.format(zdt)
    }

    fun formatRelativeStatus(isoString: String?): String {
        val instant = parseInstant(isoString) ?: return "Unscheduled"
        val now = Instant.now()
        val duration = java.time.Duration.between(now, instant)
        val minutes = duration.toMinutes()
        return when {
            minutes < -60 * 24 -> "Overdue by ${-minutes / (60 * 24)}d"
            minutes < -60 -> "Overdue by ${-minutes / 60}h"
            minutes < 0 -> "Overdue by ${-minutes}m"
            minutes == 0L -> "Due now"
            minutes < 60 -> "Due in ${minutes}m"
            minutes < 60 * 24 -> "Due in ${minutes / 60}h"
            else -> "Due in ${minutes / (60 * 24)}d"
        }
    }
}

class CommitmentService(
    private val repository: CommitmentRepository,
    private val clock: () -> Instant = { Instant.now() }
) {

    suspend fun get(actorId: String, commitmentId: String): CommitmentEntity? {
        return repository.getCommitment(actorId, commitmentId)
    }

    suspend fun capture(
        actorId: String,
        summary: String,
        rawText: String,
        dueAt: String?,
        people: List<String>,
        humanActionRequired: Boolean,
        missingInformation: List<String>
    ): CommitmentEntity {
        val now = clock()
        val questions = missingInformation.toMutableList()
        var resolvedDueAt = dueAt

        // Enforce the core Promise Pocket rule:
        // The language model or user cannot attach a due time without explicit clock wording
        if (resolvedDueAt != null && !TimeUtils.hasExplicitClockTime(rawText)) {
            resolvedDueAt = null
            if (questions.isEmpty()) {
                questions.add("What time should I bring this back?")
            }
        }

        val cleanedPeople = people.map { it.trim() }
            .filter { it.isNotEmpty() }
            .distinctBy { it.lowercase() }

        val commitment = CommitmentEntity(
            commitmentId = UUID.randomUUID().toString().replace("-", ""),
            actorId = actorId,
            summary = summary.trim(),
            rawText = rawText.trim(),
            dueAt = resolvedDueAt,
            people = cleanedPeople,
            humanActionRequired = humanActionRequired,
            missingInformation = questions,
            blockedReason = null,
            source = "chat",
            status = CommitmentStatus.PENDING,
            createdAt = now.toString(),
            updatedAt = now.toString()
        )

        repository.save(commitment)
        return commitment
    }

    suspend fun clarifyTime(
        actorId: String,
        commitmentId: String,
        answer: String,
        dueAt: String
    ): CommitmentEntity {
        val commitment = repository.getCommitment(actorId, commitmentId)
            ?: throw IllegalArgumentException("commitment was not found for this actor")

        if (!TimeUtils.hasExplicitClockTime(answer)) {
            throw IllegalArgumentException("the clarification must contain an explicit clock time (e.g. 10:00 AM, 2pm, noon)")
        }

        val remaining = commitment.missingInformation.filter {
            !it.lowercase().contains("time")
        }

        val updated = commitment.copy(
            dueAt = dueAt,
            missingInformation = remaining,
            updatedAt = clock().toString()
        )

        repository.save(updated)
        return updated
    }

    suspend fun setBlockedReason(
        actorId: String,
        commitmentId: String,
        reason: String?
    ): CommitmentEntity {
        val commitment = repository.getCommitment(actorId, commitmentId)
            ?: throw IllegalArgumentException("commitment was not found")

        val updated = commitment.copy(
            blockedReason = reason?.trim()?.ifEmpty { null },
            updatedAt = clock().toString()
        )
        repository.save(updated)
        return updated
    }

    suspend fun markStatus(
        actorId: String,
        commitmentId: String,
        newStatus: CommitmentStatus
    ): CommitmentEntity {
        val commitment = repository.getCommitment(actorId, commitmentId)
            ?: throw IllegalArgumentException("commitment was not found")

        val updated = commitment.copy(
            status = newStatus,
            updatedAt = clock().toString()
        )
        repository.save(updated)
        return updated
    }

    fun review(
        actorId: String,
        commitments: List<CommitmentEntity>,
        now: Instant = clock()
    ): List<AttentionItem> {
        val attention = mutableListOf<AttentionItem>()

        for (commitment in commitments) {
            if (commitment.actorId != actorId || commitment.status != CommitmentStatus.PENDING) {
                continue
            }

            // 1. Missing material detail needs clarification
            if (commitment.missingInformation.isNotEmpty()) {
                attention.add(
                    AttentionItem(
                        commitmentId = commitment.commitmentId,
                        summary = commitment.summary,
                        reason = AttentionReason.CLARIFICATION,
                        prompt = commitment.missingInformation.first(),
                        dueAt = commitment.dueAt,
                        people = commitment.people,
                        rawText = commitment.rawText,
                        humanActionRequired = commitment.humanActionRequired
                    )
                )
                continue
            }

            // 2. Safe progress is blocked
            if (!commitment.blockedReason.isNullOrBlank()) {
                attention.add(
                    AttentionItem(
                        commitmentId = commitment.commitmentId,
                        summary = commitment.summary,
                        reason = AttentionReason.BLOCKED,
                        prompt = commitment.blockedReason,
                        dueAt = commitment.dueAt,
                        people = commitment.people,
                        rawText = commitment.rawText,
                        humanActionRequired = commitment.humanActionRequired
                    )
                )
                continue
            }

            // 3. Due and requires personal human action
            if (commitment.humanActionRequired && commitment.dueAt != null) {
                val dueInstant = TimeUtils.parseInstant(commitment.dueAt)
                if (dueInstant != null && !dueInstant.isAfter(now)) {
                    attention.add(
                        AttentionItem(
                            commitmentId = commitment.commitmentId,
                            summary = commitment.summary,
                            reason = AttentionReason.DUE,
                            prompt = "This needs you now: ${commitment.summary}",
                            dueAt = commitment.dueAt,
                            people = commitment.people,
                            rawText = commitment.rawText,
                            humanActionRequired = commitment.humanActionRequired
                        )
                    )
                }
            }
        }

        return attention.sortedWith(
            compareBy<AttentionItem> { it.dueAt == null }
                .thenBy { it.dueAt?.let { d -> TimeUtils.parseInstant(d) } ?: now }
                .thenBy { it.commitmentId }
        )
    }
}
