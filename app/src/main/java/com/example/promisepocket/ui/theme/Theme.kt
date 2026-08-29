package com.example.promisepocket.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val LightColorScheme = lightColorScheme(
    primary = PromiseBerry,
    onPrimary = Color.White,
    primaryContainer = PromiseBlush,
    onPrimaryContainer = PromiseBerry,
    secondary = PromiseMauve,
    onSecondary = Color.White,
    secondaryContainer = PromiseCream,
    onSecondaryContainer = Slate900,
    tertiary = PromisePink,
    onTertiary = Slate900,
    tertiaryContainer = PromisePeach,
    onTertiaryContainer = Slate900,
    background = Slate50,
    onBackground = Slate900,
    surface = Color.White,
    onSurface = Slate900,
    surfaceVariant = Color(0xFFF7ECEF),
    onSurfaceVariant = Slate600,
    outline = Color(0xFFD8C8CE),
    outlineVariant = Color(0xFFECE2E5)
)

private val DarkColorScheme = darkColorScheme(
    primary = PromisePink,
    onPrimary = Slate900,
    primaryContainer = Color(0xFF3A2230),
    onPrimaryContainer = PromiseBlush,
    secondary = PromisePeach,
    onSecondary = Slate900,
    secondaryContainer = Color(0xFF49323B),
    onSecondaryContainer = PromiseCream,
    tertiary = PromiseBlush,
    onTertiary = Slate900,
    tertiaryContainer = PromiseBerry,
    onTertiaryContainer = PromiseCream,
    background = Slate900,
    onBackground = Color(0xFFF7F2F4),
    surface = Slate800,
    onSurface = Color(0xFFF8F3F5),
    surfaceVariant = Slate700,
    onSurfaceVariant = Color(0xFFD9CDD2),
    outline = Color(0xFF6F5C67),
    outlineVariant = Color(0xFF3C4658)
)

@Composable
fun PromisePocketTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = Color.Transparent.toArgb()
            window.navigationBarColor = Color.Transparent.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
            WindowCompat.getInsetsController(window, view).isAppearanceLightNavigationBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
