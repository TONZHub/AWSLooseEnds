package com.mosslet.promisepocket.data.repository

import com.mosslet.promisepocket.data.local.CommitmentDao
import com.mosslet.promisepocket.data.model.CommitmentEntity
import com.mosslet.promisepocket.data.model.CommitmentStatus
import com.mosslet.promisepocket.data.remote.CommitmentRemoteMapper
import com.mosslet.promisepocket.data.remote.MobileCaptureRequest
import com.mosslet.promisepocket.data.remote.MobileLinkRequest
import com.mosslet.promisepocket.data.remote.MobileLinkResponse
import com.mosslet.promisepocket.data.remote.MobileSessionStore
import com.mosslet.promisepocket.data.remote.ReceiptsMobileClient
import com.mosslet.promisepocket.data.remote.SyncResponse
import kotlinx.coroutines.flow.Flow

class CommitmentRepository(
    private val dao: CommitmentDao,
    private val mobileClient: ReceiptsMobileClient? = null,
    private val sessionStore: MobileSessionStore? = null
) {

    val isLinked: Boolean
        get() = sessionStore?.isLinked == true

    val currentActorId: String
        get() = sessionStore?.actorId ?: "local-user"

    fun getCommitmentsFlow(actorId: String = currentActorId): Flow<List<CommitmentEntity>> {
        return dao.getAllCommitments(actorId)
    }

    fun getCommitmentsByStatusFlow(
        actorId: String = currentActorId,
        status: CommitmentStatus
    ): Flow<List<CommitmentEntity>> {
        return dao.getCommitmentsByStatus(actorId, status)
    }

    suspend fun getCommitment(actorId: String = currentActorId, commitmentId: String): CommitmentEntity? {
        return dao.getById(actorId, commitmentId)
    }

    suspend fun listForActor(actorId: String = currentActorId): List<CommitmentEntity> {
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

    suspend fun deleteById(actorId: String = currentActorId, commitmentId: String) {
        dao.deleteById(actorId, commitmentId)
    }

    suspend fun pairMobile(code: String): Result<MobileLinkResponse> {
        val client = mobileClient ?: return Result.failure(IllegalStateException("Mobile client not configured"))
        val store = sessionStore ?: return Result.failure(IllegalStateException("Session store not configured"))
        return try {
            val response = client.service.link(
                MobileLinkRequest(code = code.trim(), installation_id = store.installationId)
            )
            if (response.linked) {
                store.save(response)
                syncWithCloud(response.actor_id)
                Result.success(response)
            } else {
                Result.failure(IllegalStateException("Invalid or expired pairing code"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun captureRemote(text: String, sourceId: String = "android-app"): Result<SyncResponse> {
        val client = mobileClient ?: return Result.failure(IllegalStateException("Mobile client not configured"))
        return try {
            val response = client.service.capture(MobileCaptureRequest(text = text, source_id = sourceId))
            syncWithCloud()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun transitionCommitment(commitmentId: String, action: String): Result<SyncResponse> {
        val client = mobileClient ?: return Result.failure(IllegalStateException("Mobile client not configured"))
        return try {
            val response = client.service.transition(commitmentId = commitmentId, action = action)
            syncWithCloud()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun syncWithCloud(actorId: String = currentActorId) {
        // When linked to Receipts watcher, sync with the shared ledger
        if (mobileClient != null && sessionStore?.isLinked == true) {
            try {
                val response = mobileClient.service.listCommitments()
                response.items?.forEach { remote ->
                    val entity = CommitmentRemoteMapper.toEntity(remote)
                    val local = dao.getById(entity.actorId, entity.commitmentId)
                    if (local == null) {
                        dao.insert(entity)
                    } else {
                        dao.update(entity)
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
