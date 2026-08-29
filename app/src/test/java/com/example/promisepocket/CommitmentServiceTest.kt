package com.example.promisepocket

import com.example.promisepocket.data.local.CommitmentDao
import com.example.promisepocket.data.model.AttentionReason
import com.example.promisepocket.data.model.CommitmentEntity
import com.example.promisepocket.data.model.CommitmentStatus
import com.example.promisepocket.data.repository.CommitmentRepository
import com.example.promisepocket.domain.CommitmentService
import com.example.promisepocket.domain.TimeUtils
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.time.Instant
import java.time.temporal.ChronoUnit

class FakeCommitmentDao : CommitmentDao {
    private val store = mutableMapOf<String, CommitmentEntity>()

    override fun getAllCommitments(actorId: String): Flow<List<CommitmentEntity>> {
        return flowOf(store.values.filter { it.actorId == actorId })
    }

    override fun getCommitmentsByStatus(
        actorId: String,
        status: CommitmentStatus
    ): Flow<List<CommitmentEntity>> {
        return flowOf(store.values.filter { it.actorId == actorId && it.status == status })
    }

    override suspend fun getById(actorId: String, commitmentId: String): CommitmentEntity? {
        val item = store[commitmentId]
        return if (item?.actorId == actorId) item else null
    }

    override suspend fun getListForActor(actorId: String): List<CommitmentEntity> {
        return store.values.filter { it.actorId == actorId }
    }

    override suspend fun insert(commitment: CommitmentEntity) {
        store[commitment.commitmentId] = commitment
    }

    override suspend fun insertAll(commitments: List<CommitmentEntity>) {
        commitments.forEach { store[it.commitmentId] = it }
    }

    override suspend fun update(commitment: CommitmentEntity) {
        store[commitment.commitmentId] = commitment
    }

    override suspend fun delete(commitment: CommitmentEntity) {
        store.remove(commitment.commitmentId)
    }

    override suspend fun deleteById(actorId: String, commitmentId: String) {
        val item = store[commitmentId]
        if (item?.actorId == actorId) {
            store.remove(commitmentId)
        }
    }
}

class CommitmentServiceTest {

    private lateinit var dao: FakeCommitmentDao
    private lateinit var repository: CommitmentRepository
    private lateinit var service: CommitmentService
    private val now = Instant.parse("2026-08-29T12:00:00Z")

    @Before
    fun setUp() {
        dao = FakeCommitmentDao()
        repository = CommitmentRepository(dao)
        service = CommitmentService(repository, clock = { now })
    }

    private suspend fun capture(
        actorId: String = "zoe",
        summary: String = "Call the dentist for Mom",
        rawText: String = "I promised Mom I would call the dentist tomorrow at noon",
        dueAt: String? = now.plus(1, ChronoUnit.DAYS).toString(),
        people: List<String> = listOf("Mom"),
        humanActionRequired: Boolean = true,
        missingInformation: List<String> = emptyList()
    ): CommitmentEntity {
        return service.capture(
            actorId = actorId,
            summary = summary,
            rawText = rawText,
            dueAt = dueAt,
            people = people,
            humanActionRequired = humanActionRequired,
            missingInformation = missingInformation
        )
    }

    @Test
    fun testCapturePersistsExactCommitment() = runBlocking {
        val captured = capture()
        val stored = repository.listForActor("zoe")

        assertEquals(1, stored.size)
        assertEquals(captured.commitmentId, stored[0].commitmentId)
        assertEquals(listOf("Mom"), stored[0].people)
        assertEquals(now.plus(1, ChronoUnit.DAYS).toString(), stored[0].dueAt)
    }

    @Test
    fun testFutureCommitmentDoesNotInterrupt() = runBlocking {
        capture()
        val all = repository.listForActor("zoe")
        val attention = service.review(actorId = "zoe", commitments = all, now = now)

        assertTrue(attention.isEmpty())
    }

    @Test
    fun testDueHumanActionInterrupts() = runBlocking {
        val captured = capture(dueAt = now.minus(1, ChronoUnit.MINUTES).toString())
        val all = repository.listForActor("zoe")
        val attention = service.review(actorId = "zoe", commitments = all, now = now)

        assertEquals(1, attention.size)
        assertEquals(captured.commitmentId, attention[0].commitmentId)
        assertEquals(AttentionReason.DUE, attention[0].reason)
    }

    @Test
    fun testDueAgentSafeWorkStaysQuiet() = runBlocking {
        capture(
            summary = "Prepare dentist options",
            dueAt = now.minus(1, ChronoUnit.MINUTES).toString(),
            humanActionRequired = false
        )
        val all = repository.listForActor("zoe")
        val attention = service.review(actorId = "zoe", commitments = all, now = now)

        assertTrue(attention.isEmpty())
    }

    @Test
    fun testMissingInformationSurfacesOneQuestion() = runBlocking {
        capture(
            dueAt = null,
            missingInformation = listOf("When should I bring this back?")
        )
        val all = repository.listForActor("zoe")
        val attention = service.review(actorId = "zoe", commitments = all, now = now)

        assertEquals(1, attention.size)
        assertEquals(AttentionReason.CLARIFICATION, attention[0].reason)
        assertEquals("When should I bring this back?", attention[0].prompt)
    }

    @Test
    fun testCannotInventClockTimeForDateOnlyWords() = runBlocking {
        val captured = capture(
            rawText = "I need to call the pharmacy tomorrow",
            dueAt = now.plus(15, ChronoUnit.HOURS).toString()
        )

        assertNull(captured.dueAt)
        assertEquals(listOf("What time should I bring this back?"), captured.missingInformation)
    }

    @Test
    fun testTimeClarificationUpdatesSameRecord() = runBlocking {
        val captured = capture(
            rawText = "I need to call the pharmacy tomorrow",
            dueAt = now.plus(15, ChronoUnit.HOURS).toString()
        )
        val resolved = now.plus(1, ChronoUnit.DAYS).plus(2, ChronoUnit.HOURS).toString()

        val updated = service.clarifyTime(
            actorId = "zoe",
            commitmentId = captured.commitmentId,
            answer = "10:00",
            dueAt = resolved
        )

        assertEquals(captured.commitmentId, updated.commitmentId)
        assertEquals(resolved, updated.dueAt)
        assertTrue(updated.missingInformation.isEmpty())
        assertEquals(1, repository.listForActor("zoe").size)
    }

    @Test
    fun testActorRecordsAreIsolated() = runBlocking {
        capture(actorId = "zoe", dueAt = now.minus(1, ChronoUnit.MINUTES).toString())
        capture(actorId = "someone-else", dueAt = now.minus(1, ChronoUnit.MINUTES).toString())

        val zoeItems = repository.listForActor("zoe")
        val attention = service.review(actorId = "zoe", commitments = zoeItems, now = now)

        assertEquals(1, attention.size)
    }
}
