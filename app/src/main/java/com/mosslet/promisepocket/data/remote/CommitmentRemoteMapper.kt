package com.mosslet.promisepocket.data.remote

import com.mosslet.promisepocket.data.model.CommitmentEntity
import com.mosslet.promisepocket.data.model.CommitmentStatus

object CommitmentRemoteMapper {
    fun toEntity(remote: CommitmentRemoteEntity): CommitmentEntity {
        return CommitmentEntity(
            commitmentId = remote.commitment_id,
            actorId = remote.actor_id,
            summary = remote.summary,
            rawText = remote.raw_text,
            status = try { CommitmentStatus.valueOf(remote.status) } catch (e: Exception) { CommitmentStatus.PENDING },
            dueAt = remote.due_at,
            people = remote.people,
            blockedReason = remote.blocked_reason,
            humanActionRequired = remote.human_action_required,
            missingInformation = remote.missing_information
        )
    }

    fun toRemote(entity: CommitmentEntity): CommitmentRemoteEntity {
        return CommitmentRemoteEntity(
            commitment_id = entity.commitmentId,
            actor_id = entity.actorId,
            summary = entity.summary,
            raw_text = entity.rawText,
            status = entity.status.name,
            due_at = entity.dueAt,
            people = entity.people,
            blocked_reason = entity.blockedReason,
            human_action_required = entity.humanActionRequired,
            missing_information = entity.missingInformation
        )
    }
}
