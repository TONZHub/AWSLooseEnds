package com.mosslet.promisepocket.data.repository

import com.mosslet.promisepocket.data.local.CommitmentDao
import com.mosslet.promisepocket.data.model.CommitmentEntity
import com.mosslet.promisepocket.data.model.CommitmentStatus
import com.mosslet.promisepocket.data.remote.CommitmentRemoteMapper
import com.mosslet.promisepocket.data.remote.RetrofitClient
import com.mosslet.promisepocket.data.remote.SyncRequest
import kotlinx.coroutines.flow.Flow

class CommitmentRepository(private val dao: CommitmentDao) {

    fun getCommitmentsFlow(actorId: String): Flow<List<CommitmentEntity>> {
        return dao.getAllCommitments(actorId)
    }

    fun getCommitmentsByStatusFlow(actorId: String, status: CommitmentStatus): Flow<List<CommitmentEntity>> {
        return dao.getCommitmentsByStatus(actorId, status)
    }

    suspend fun getCommitment(actorId: String, commitmentId: String): CommitmentEntity? {
        return dao.getById(actorId, commitmentId)
    }

    suspend fun listForActor(actorId: String): List<CommitmentEntity> {
        return dao.getListForActor(actorId)
    }

    suspend fun save(commitment: CommitmentEntity) {
        dao.insert(commitment)
    }

    suspend fun update(commitment: CommitmentEntity) {
        dao.update(commitment)
    }

    suspend fun delete(commitment: CommitmentEntity) {
        dao.delete(commitment)
    }

    suspend fun deleteById(actorId: String, commitmentId: String) {
        dao.deleteById(actorId, commitmentId)
    }

    suspend fun syncWithCloud(actorId: String) {
        if (actorId == "local-user") return

        try {
            val response = RetrofitClient.backendService.invokeOperation(
                SyncRequest(operation = "review", actor_id = actorId)
            )

            response.items?.forEach { remote ->
                val local = dao.getById(actorId, remote.commitment_id)
                if (local == null) {
                    dao.insert(CommitmentRemoteMapper.toEntity(remote))
                } else {
                    // Simple sync logic: remote wins for now
                    dao.update(CommitmentRemoteMapper.toEntity(remote))
                }
            }
        } catch (e: Exception) {
            // Log error or handle gracefully
            e.printStackTrace()
        }
    }
}
