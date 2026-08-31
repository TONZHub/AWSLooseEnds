package com.mosslet.promisepocket.ui.theme

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
    onPrimary = PromiseCream,
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
    background = Slate900,
    onBackground = PromiseCream,
    surface = Slate50,
    onSurface = Slate900,
    surfaceVariant = Slate100,
    onSurfaceVariant = Slate600,
    outline = Slate700,
    outlineVariant = Slate200
)

private val DarkColorScheme = darkColorScheme(
    primary = PromisePink,
    onPrimary = Slate900,
    primaryContainer = PromisePinkDark,
    onPrimaryContainer = PromiseBlush,
    secondary = PromisePeach,
    onSecondary = Slate900,
    secondaryContainer = Slate700,
    onSecondaryContainer = PromiseCream,
    tertiary = PromiseBlush,
    onTertiary = Slate900,
    tertiaryContainer = PromiseBerry,
    onTertiaryContainer = PromiseCream,
    background = Slate900,
    onBackground = PromiseCream,
    surface = Slate50,
    onSurface = Slate900,
    surfaceVariant = Slate100,
    onSurfaceVariant = Slate600,
    outline = Slate700,
    outlineVariant = Slate200
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
