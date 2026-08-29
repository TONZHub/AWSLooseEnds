package com.mosslet.promisepocket.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val DarkColorScheme = darkColorScheme(
    primary = PromiseBlue,
    secondary = QuietGray,
    tertiary = AttentionRed,
    background = QuietBlack,
    surface = QuietBlack,
    onPrimary = QuietWhite,
    onSecondary = QuietWhite,
    onTertiary = QuietWhite,
    onBackground = QuietWhite,
    onSurface = QuietWhite,
)

private val LightColorScheme = lightColorScheme(
    primary = PromiseBlue,
    secondary = QuietGray,
    tertiary = AttentionRed,
    background = QuietWhite,
    surface = QuietWhite,
    onPrimary = QuietBlack,
    onSecondary = QuietBlack,
    onTertiary = QuietBlack,
    onBackground = QuietBlack,
    onSurface = QuietBlack,
)

@Composable
fun PromisePocketTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.background.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
