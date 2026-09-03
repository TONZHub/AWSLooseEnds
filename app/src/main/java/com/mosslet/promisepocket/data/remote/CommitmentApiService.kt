package com.mosslet.promisepocket.data.remote

import kotlinx.serialization.Serializable
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Path
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
data class MobileLinkRequest(
    val code: String,
    val installation_id: String
)

@Serializable
data class MobileLinkResponse(
    val linked: Boolean,
    val token: String,
    val actor_id: String
)

@Serializable
data class MobileCaptureRequest(
    val text: String,
    val source_id: String
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

@Serializable
data class MobileUnlinkResponse(
    val unlinked: Boolean = true,
    val revoked: Boolean = true
)

interface CommitmentApiService {
    // Retained until the ViewModel is migrated to the mobile pairing client.
    @POST("invoke")
    suspend fun invokeOperation(@Body request: SyncRequest): SyncResponse

    @POST("link")
    suspend fun link(@Body request: MobileLinkRequest): MobileLinkResponse

    @POST("unlink")
    suspend fun unlink(): MobileUnlinkResponse

    @GET("commitments")
    suspend fun listCommitments(): SyncResponse

    @POST("capture")
    suspend fun capture(@Body request: MobileCaptureRequest): SyncResponse

    @POST("commitments/{commitmentId}/{action}")
    suspend fun transition(
        @Path("commitmentId") commitmentId: String,
        @Path("action") action: String
    ): SyncResponse
}
