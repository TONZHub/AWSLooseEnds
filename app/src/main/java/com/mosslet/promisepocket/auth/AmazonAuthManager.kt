package com.mosslet.promisepocket.auth

import androidx.activity.ComponentActivity
import com.amazon.identity.auth.device.AuthError
import com.amazon.identity.auth.device.api.Listener
import com.amazon.identity.auth.device.api.authorization.AuthCancellation
import com.amazon.identity.auth.device.api.authorization.AuthorizationManager
import com.amazon.identity.auth.device.api.authorization.AuthorizeListener
import com.amazon.identity.auth.device.api.authorization.AuthorizeRequest
import com.amazon.identity.auth.device.api.authorization.AuthorizeResult
import com.amazon.identity.auth.device.api.authorization.ProfileScope
import com.amazon.identity.auth.device.api.authorization.User
import com.amazon.identity.auth.device.api.workflow.RequestContext

data class AmazonAccount(
    val actorId: String,
    val name: String?,
    val email: String?
)

sealed interface AmazonAuthResult {
    data object Loading : AmazonAuthResult
    data object SignedOut : AmazonAuthResult
    data object Cancelled : AmazonAuthResult
    data class SignedIn(val account: AmazonAccount) : AmazonAuthResult
    data class Error(val message: String) : AmazonAuthResult
}

/** Lifecycle-aware adapter around Amazon's Android Login with Amazon SDK. */
class AmazonAuthManager(
    private val activity: ComponentActivity,
    private val onResult: (AmazonAuthResult) -> Unit
) {
    private val requestContext = RequestContext.create(activity)
    private val scopes = arrayOf(ProfileScope.profile())

    init {
        requestContext.registerListener(object : AuthorizeListener() {
            override fun onSuccess(result: AuthorizeResult) {
                fetchProfile()
            }

            override fun onError(error: AuthError) {
                publish(
                    AmazonAuthResult.Error(
                        "Amazon sign-in couldn't finish. Check the app registration and try again."
                    )
                )
            }

            override fun onCancel(cancellation: AuthCancellation) {
                publish(AmazonAuthResult.Cancelled)
            }
        })
    }

    fun onResume() {
        requestContext.onResume()
    }

    fun restoreSession() {
        if (!isConfigured()) {
            publish(AmazonAuthResult.SignedOut)
            return
        }

        publish(AmazonAuthResult.Loading)
        AuthorizationManager.getToken(
            activity,
            scopes,
            object : Listener<AuthorizeResult, AuthError> {
                override fun onSuccess(result: AuthorizeResult) {
                    if (result.accessToken.isNullOrBlank()) {
                        publish(AmazonAuthResult.SignedOut)
                    } else {
                        fetchProfile()
                    }
                }

                override fun onError(error: AuthError) {
                    publish(
                        AmazonAuthResult.Error(
                            "Promise Pocket couldn't check the Amazon session. Try again when online."
                        )
                    )
                }
            }
        )
    }

    fun signIn() {
        if (!isConfigured()) {
            publish(
                AmazonAuthResult.Error(
                    "Amazon sign-in needs this build's Login with Amazon API key."
                )
            )
            return
        }

        publish(AmazonAuthResult.Loading)
        AuthorizationManager.authorize(
            AuthorizeRequest.Builder(requestContext)
                .addScopes(*scopes)
                .build()
        )
    }

    fun signOut() {
        publish(AmazonAuthResult.Loading)
        AuthorizationManager.signOut(
            activity.applicationContext,
            object : Listener<Void, AuthError> {
                override fun onSuccess(response: Void?) {
                    publish(AmazonAuthResult.SignedOut)
                }

                override fun onError(error: AuthError) {
                    publish(AmazonAuthResult.Error("Amazon sign-out couldn't finish. Try again."))
                }
            }
        )
    }

    private fun fetchProfile() {
        User.fetch(activity, object : Listener<User, AuthError> {
            override fun onSuccess(user: User) {
                val userId = user.userId?.trim()
                if (userId.isNullOrEmpty()) {
                    publish(AmazonAuthResult.Error("Amazon didn't return an account identifier."))
                    return
                }

                publish(
                    AmazonAuthResult.SignedIn(
                        AmazonAccount(
                            actorId = amazonActorId(userId),
                            name = user.userName?.trim()?.takeIf(String::isNotEmpty),
                            email = user.userEmail?.trim()?.takeIf(String::isNotEmpty)
                        )
                    )
                )
            }

            override fun onError(error: AuthError) {
                publish(
                    AmazonAuthResult.Error(
                        "Amazon signed in, but the account profile couldn't be loaded."
                    )
                )
            }
        })
    }

    private fun isConfigured(): Boolean = runCatching {
        activity.assets.open("api_key.txt").bufferedReader().use { reader ->
            reader.readText().trim().isNotEmpty()
        }
    }.getOrDefault(false)

    private fun publish(result: AmazonAuthResult) {
        activity.runOnUiThread { onResult(result) }
    }
}
