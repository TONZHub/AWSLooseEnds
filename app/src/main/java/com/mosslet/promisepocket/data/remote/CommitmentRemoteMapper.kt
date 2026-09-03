package com.mosslet.promisepocket.data.remote

import com.mosslet.promisepocket.data.model.CommitmentEntity
import com.mosslet.promisepocket.data.model.CommitmentStatus

object CommitmentRemoteMapper {
    fun parseStatus(raw: String?): CommitmentStatus {
        if (raw.isNullOrBlank()) return CommitmentStatus.PENDING
        val normalized = raw.trim().uppercase()
        return when (normalized) {
            "CANDIDATE" -> CommitmentStatus.CANDIDATE
            "ACTIVE" -> CommitmentStatus.ACTIVE
            "LIKELY_DONE" -> CommitmentStatus.LIKELY_DONE
            "DONE" -> CommitmentStatus.DONE
            "OVERDUE" -> CommitmentStatus.OVERDUE
            "COMPLETED" -> CommitmentStatus.COMPLETED
            "CANCELED" -> CommitmentStatus.CANCELED
            "PENDING" -> CommitmentStatus.PENDING
            else -> try {
                CommitmentStatus.valueOf(normalized)
            } catch (_: Exception) {
                CommitmentStatus.PENDING
            }
        }
    }

    fun toEntity(remote: CommitmentRemoteEntity): CommitmentEntity {
        return CommitmentEntity(
            commitmentId = remote.commitment_id,
            actorId = remote.actor_id,
            summary = remote.summary,
            rawText = remote.raw_text,
            status = parseStatus(remote.status),
            dueAt = remote.due_at,
            people = remote.people,
            blockedReason = remote.blocked_reason,
            humanActionRequired = remote.human_action_required || parseStatus(remote.status) == CommitmentStatus.CANDIDATE,
            missingInformation = remote.missing_information
        )
    }

    fun toRemote(entity: CommitmentEntity): CommitmentRemoteEntity {
        return CommitmentRemoteEntity(
            commitment_id = entity.commitmentId,
            actor_id = entity.actorId,
            summary = entity.summary,
            raw_text = entity.rawText,
            status = entity.status.value,
            due_at = entity.dueAt,
            people = entity.people,
            blocked_reason = entity.blockedReason,
            human_action_required = entity.humanActionRequired,
            missing_information = entity.missingInformation
        )
    }
}
