package com.example.promisepocket

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.example.promisepocket.auth.AmazonAuthManager
import com.example.promisepocket.ui.screens.MainScreen
import com.example.promisepocket.ui.theme.PromisePocketTheme
import com.example.promisepocket.ui.viewmodel.PromisePocketViewModel

class MainActivity : ComponentActivity() {

    private val viewModel: PromisePocketViewModel by viewModels()
    private lateinit var amazonAuthManager: AmazonAuthManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        amazonAuthManager = AmazonAuthManager(this, viewModel::onAmazonAuthResult)
        enableEdgeToEdge()
        setContent {
            PromisePocketTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    MainScreen(
                        viewModel = viewModel,
                        onSignInWithAmazon = amazonAuthManager::signIn,
                        onSignOutFromAmazon = amazonAuthManager::signOut
                    )
                }
            }
        }
    }

    override fun onStart() {
        super.onStart()
        amazonAuthManager.restoreSession()
    }

    override fun onResume() {
        super.onResume()
        amazonAuthManager.onResume()
    }
}
