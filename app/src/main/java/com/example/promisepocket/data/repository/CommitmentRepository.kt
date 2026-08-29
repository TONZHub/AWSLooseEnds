package com.example.promisepocket.data.repository

import com.example.promisepocket.data.local.CommitmentDao
import com.example.promisepocket.data.model.CommitmentEntity
import com.example.promisepocket.data.model.CommitmentStatus
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
}
