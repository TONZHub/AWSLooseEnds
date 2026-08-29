package com.mosslet.promisepocket.data.local

import androidx.room.TypeConverter
import com.mosslet.promisepocket.data.model.CommitmentStatus
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

class Converters {
    private val json = Json { ignoreUnknownKeys = true }

    @TypeConverter
    fun fromStringList(value: List<String>): String {
        return json.encodeToString(value)
    }

    @TypeConverter
    fun toStringList(value: String): List<String> {
        return try {
            json.decodeFromString(value)
        } catch (e: Exception) {
            emptyList()
        }
    }

    @TypeConverter
    fun fromCommitmentStatus(status: CommitmentStatus): String {
        return status.value
    }

    @TypeConverter
    fun toCommitmentStatus(value: String): CommitmentStatus {
        return when (value.lowercase()) {
            "completed" -> CommitmentStatus.COMPLETED
            "canceled" -> CommitmentStatus.CANCELED
            else -> CommitmentStatus.PENDING
        }
    }
}
