package com.mosslet.promisepocket.data.remote

import kotlinx.serialization.Serializable
import retrofit2.http.Body
import retrofit2.http.POST

@Serializable
data class SyncRequest(
    val operation: String,
    val actor_id: String,
    val prompt: String? = null,
    val commitment_id: String? = null,
    val answer: String? = null,
    val timezone: String? = null,
    val now: String? = null
)

@Serializable
data class SyncResponse(
    val operation: String,
    val attention_required: Boolean? = null,
    val items: List<CommitmentRemoteEntity>? = null,
    val captured_commitment_ids: List<String>? = null,
    val updated_commitment_ids: List<String>? = null,
    val result: String? = null
)

@Serializable
data class CommitmentRemoteEntity(
    val commitment_id: String,
    val actor_id: String,
    val summary: String,
    val raw_text: String,
    val status: String,
    val due_at: String? = null,
    val people: List<String> = emptyList(),
    val blocked_reason: String? = null,
    val human_action_required: Boolean = false,
    val missing_information: List<String> = emptyList()
)

interface CommitmentApiService {
    @POST("invoke")
    suspend fun invokeOperation(@Body request: SyncRequest): SyncResponse
}
