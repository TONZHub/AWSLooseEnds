package com.example.promisepocket.auth

import java.security.MessageDigest

/**
 * Builds the ledger identity shared by the Android app and an account-linked
 * Alexa skill. The raw Login with Amazon identifier never enters storage.
 */
fun amazonActorId(amazonUserId: String): String {
    require(amazonUserId.isNotBlank()) { "Amazon user ID cannot be blank" }
    val digest = MessageDigest.getInstance("SHA-256")
        .digest(amazonUserId.toByteArray(Charsets.UTF_8))
        .joinToString(separator = "") { byte -> "%02x".format(byte.toInt() and 0xff) }
    return "amazon-$digest"
}
