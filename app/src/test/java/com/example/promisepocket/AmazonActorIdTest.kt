package com.example.promisepocket

import com.example.promisepocket.auth.amazonActorId
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class AmazonActorIdTest {
    @Test
    fun loginWithAmazonIdentityMatchesBackendHashContract() {
        assertEquals(
            "amazon-43c29fcd70d239ecda137d6bb3c52b713d45d90196ecee0e67f6dfa24cb62de9",
            amazonActorId("amazon-user-123")
        )
    }

    @Test
    fun blankAmazonIdentityIsRejected() {
        assertThrows(IllegalArgumentException::class.java) { amazonActorId("  ") }
    }
}
