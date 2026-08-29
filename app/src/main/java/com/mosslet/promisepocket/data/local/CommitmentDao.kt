package com.mosslet.promisepocket.data.local

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.mosslet.promisepocket.data.model.CommitmentEntity
import com.mosslet.promisepocket.data.model.CommitmentStatus
import kotlinx.coroutines.flow.Flow

@Dao
interface CommitmentDao {

    @Query("SELECT * FROM commitments WHERE actorId = :actorId ORDER BY createdAt DESC")
    fun getAllCommitments(actorId: String): Flow<List<CommitmentEntity>>

    @Query("SELECT * FROM commitments WHERE actorId = :actorId AND status = :status ORDER BY createdAt DESC")
    fun getCommitmentsByStatus(actorId: String, status: CommitmentStatus): Flow<List<CommitmentEntity>>

    @Query("SELECT * FROM commitments WHERE actorId = :actorId AND commitmentId = :commitmentId LIMIT 1")
    suspend fun getById(actorId: String, commitmentId: String): CommitmentEntity?

    @Query("SELECT * FROM commitments WHERE actorId = :actorId")
    suspend fun getListForActor(actorId: String): List<CommitmentEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(commitment: CommitmentEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(commitments: List<CommitmentEntity>)

    @Update
    suspend fun update(commitment: CommitmentEntity)

    @Delete
    suspend fun delete(commitment: CommitmentEntity)

    @Query("DELETE FROM commitments WHERE actorId = :actorId AND commitmentId = :commitmentId")
    suspend fun deleteById(actorId: String, commitmentId: String)
}
