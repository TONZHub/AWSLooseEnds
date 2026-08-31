package com.mosslet.promisepocket.data.remote

import android.content.Context
import com.mosslet.promisepocket.BuildConfig
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory

class ReceiptsMobileClient(context: Context) {
    private val sessions = MobileSessionStore(context)
    private val http = OkHttpClient.Builder()
        .addInterceptor { chain ->
            val token = sessions.token
            val request = if (token.isNullOrBlank()) {
                chain.request()
            } else {
                chain.request().newBuilder()
                    .header("Authorization", "Bearer $token")
                    .build()
            }
            chain.proceed(request)
        }
        .build()

    val service: CommitmentApiService = Retrofit.Builder()
        .baseUrl(normalizedBaseUrl())
        .client(http)
        .addConverterFactory(
            RetrofitClient.json.asConverterFactory("application/json".toMediaType())
        )
        .build()
        .create(CommitmentApiService::class.java)

    private fun normalizedBaseUrl(): String {
        val configured = BuildConfig.RECEIPTS_API_BASE_URL.trim()
        require(configured.startsWith("https://")) {
            "RECEIPTS_API_BASE_URL must use HTTPS"
        }
        return configured.trimEnd('/') + "/"
    }
}
