package com.mosslet.promisepocket.data.remote

import android.content.Context
import java.util.UUID

class MobileSessionStore(context: Context) {
    private val preferences = context.getSharedPreferences("receipts_mobile", Context.MODE_PRIVATE)

    val installationId: String
        get() {
            val existing = preferences.getString(KEY_INSTALLATION_ID, null)
            if (!existing.isNullOrBlank()) return existing
            val created = UUID.randomUUID().toString()
            preferences.edit().putString(KEY_INSTALLATION_ID, created).apply()
            return created
        }

    val token: String?
        get() = preferences.getString(KEY_TOKEN, null)

    val actorId: String?
        get() = preferences.getString(KEY_ACTOR_ID, null)

    val isLinked: Boolean
        get() = !token.isNullOrBlank() && !actorId.isNullOrBlank()

    fun save(link: MobileLinkResponse) {
        preferences.edit()
            .putString(KEY_TOKEN, link.token)
            .putString(KEY_ACTOR_ID, link.actor_id)
            .apply()
    }

    fun clear() {
        preferences.edit()
            .remove(KEY_TOKEN)
            .remove(KEY_ACTOR_ID)
            .apply()
    }

    private companion object {
        const val KEY_INSTALLATION_ID = "installation_id"
        const val KEY_TOKEN = "token"
        const val KEY_ACTOR_ID = "actor_id"
    }
}
