package com.mosslet.promisepocket

import com.mosslet.promisepocket.data.local.CommitmentDao
import com.mosslet.promisepocket.data.model.CommitmentEntity
import com.mosslet.promisepocket.data.model.CommitmentStatus
import com.mosslet.promisepocket.data.remote.CommitmentApiService
import com.mosslet.promisepocket.data.remote.CommitmentRemoteEntity
import com.mosslet.promisepocket.data.remote.CommitmentRemoteMapper
import com.mosslet.promisepocket.data.remote.MobileCaptureRequest
import com.mosslet.promisepocket.data.remote.MobileLinkRequest
import com.mosslet.promisepocket.data.remote.MobileLinkResponse
import com.mosslet.promisepocket.data.remote.ReceiptsMobileClient
import com.mosslet.promisepocket.data.remote.SyncRequest
import com.mosslet.promisepocket.data.remote.SyncResponse
import com.mosslet.promisepocket.data.repository.CommitmentRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class FakeMobileApiService : CommitmentApiService {
    var lastCapturedRequest: MobileCaptureRequest? = null
    var lastTransitionAction: String? = null
    var lastTransitionCommitmentId: String? = null
    var remoteCommitments = mutableListOf<CommitmentRemoteEntity>()

    override suspend fun invokeOperation(request: SyncRequest): SyncResponse {
        return SyncResponse(operation = request.operation)
    }

    override suspend fun link(request: MobileLinkRequest): MobileLinkResponse {
        return if (request.code == "123456") {
            MobileLinkResponse(
                linked = true,
                token = "mock-bearer-token-xyz",
                actor_id = "mobile-actor-hash"
            )
        } else {
            MobileLinkResponse(
                linked = false,
                token = "",
                actor_id = ""
            )
        }
    }

    override suspend fun listCommitments(): SyncResponse {
        return SyncResponse(
            operation = "list",
            items = remoteCommitments.toList()
        )
    }

    override suspend fun capture(request: MobileCaptureRequest): SyncResponse {
        lastCapturedRequest = request
        val id = "c-" + System.currentTimeMillis()
        val created = CommitmentRemoteEntity(
            commitment_id = id,
            actor_id = "mobile-actor-hash",
            summary = request.text.take(30),
            raw_text = request.text,
            status = "active"
        )
        remoteCommitments.add(created)
        return SyncResponse(
            operation = "capture",
            captured_commitment_ids = listOf(id),
            items = listOf(created)
        )
    }

    override suspend fun transition(commitmentId: String, action: String): SyncResponse {
        lastTransitionCommitmentId = commitmentId
        lastTransitionAction = action
        val index = remoteCommitments.indexOfFirst { it.commitment_id == commitmentId }
        if (index >= 0) {
            val old = remoteCommitments[index]
            val newStatus = when (action) {
                "confirm" -> "active"
                "done" -> "done"
                "reopen" -> "active"
                "cancel" -> "canceled"
                else -> old.status
            }
            remoteCommitments[index] = old.copy(status = newStatus)
        }
        return SyncResponse(
            operation = "transition",
            updated_commitment_ids = listOf(commitmentId)
        )
    }
}

class ReceiptsMobileSyncTest {

    private lateinit var dao: FakeCommitmentDao
    private lateinit var fakeApi: FakeMobileApiService

    @Before
    fun setUp() {
        dao = FakeCommitmentDao()
        fakeApi = FakeMobileApiService()
    }

    @Test
    fun testStatusParsingAndMapping() {
        assertEquals(CommitmentStatus.CANDIDATE, CommitmentRemoteMapper.parseStatus("candidate"))
        assertEquals(CommitmentStatus.CANDIDATE, CommitmentRemoteMapper.parseStatus("CANDIDATE"))
        assertEquals(CommitmentStatus.ACTIVE, CommitmentRemoteMapper.parseStatus("active"))
        assertEquals(CommitmentStatus.LIKELY_DONE, CommitmentRemoteMapper.parseStatus("likely_done"))
        assertEquals(CommitmentStatus.DONE, CommitmentRemoteMapper.parseStatus("done"))
        assertEquals(CommitmentStatus.OVERDUE, CommitmentRemoteMapper.parseStatus("overdue"))
        assertEquals(CommitmentStatus.CANCELED, CommitmentRemoteMapper.parseStatus("canceled"))
        assertEquals(CommitmentStatus.PENDING, CommitmentRemoteMapper.parseStatus("unknown_weird_status"))

        val remote = CommitmentRemoteEntity(
            commitment_id = "c-100",
            actor_id = "actor-1",
            summary = "Deliver test plan",
            raw_text = "I promised to deliver test plan by tomorrow",
            status = "candidate",
            due_at = "2026-09-04T12:00:00Z",
            people = listOf("Alex"),
            human_action_required = true
        )
        val entity = CommitmentRemoteMapper.toEntity(remote)
        assertEquals(CommitmentStatus.CANDIDATE, entity.status)
        assertEquals("c-100", entity.commitmentId)
        assertEquals("actor-1", entity.actorId)

        val wire = CommitmentRemoteMapper.toRemote(entity)
        assertEquals("candidate", wire.status)
    }

    @Test
    fun testRemoteTransitionExplicitActions() = runBlocking {
        fakeApi.remoteCommitments.add(
            CommitmentRemoteEntity(
                commitment_id = "c-candidate-1",
                actor_id = "mobile-actor-hash",
                summary = "Candidate promise from email",
                raw_text = "Will review PR tomorrow",
                status = "candidate"
            )
        )

        // Simulate transition action via fakeApi
        fakeApi.transition("c-candidate-1", "confirm")
        assertEquals("c-candidate-1", fakeApi.lastTransitionCommitmentId)
        assertEquals("confirm", fakeApi.lastTransitionAction)
        assertEquals("active", fakeApi.remoteCommitments[0].status)

        fakeApi.transition("c-candidate-1", "done")
        assertEquals("done", fakeApi.lastTransitionAction)
        assertEquals("done", fakeApi.remoteCommitments[0].status)
    }

    @Test
    fun testCandidateAuthorityInvariant() {
        // Core Authority Rule test: candidates require explicit human confirmation
        val candidate = CommitmentRemoteEntity(
            commitment_id = "c-voice-1",
            actor_id = "mobile-actor-hash",
            summary = "Voice captured intent",
            raw_text = "remind me to call the accountant",
            status = "candidate"
        )
        val entity = CommitmentRemoteMapper.toEntity(candidate)
        assertEquals(CommitmentStatus.CANDIDATE, entity.status)
        assertTrue("Human action required should be true for candidates", entity.humanActionRequired)
    }
}
