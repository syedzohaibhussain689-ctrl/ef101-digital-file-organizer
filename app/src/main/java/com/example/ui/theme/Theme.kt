package com.example.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Connects our custom colors from Color.kt into Android's Material 3 theme system.
// Setting onPrimary to White makes sure that any text inside dark primary buttons stays crisp white.
private val ColorScheme = lightColorScheme(
    primary = ACCENT,
    onPrimary = Color.White,
    primaryContainer = ACCENT_SOFT,
    onPrimaryContainer = TEXT,
    secondary = TEXT_SEC,
    onSecondary = Color.White,
    secondaryContainer = BORDER_LIGHT,
    onSecondaryContainer = TEXT,
    background = BG,
    onBackground = TEXT,
    surface = SURFACE,
    onSurface = TEXT,
    surfaceVariant = BG,
    onSurfaceVariant = TEXT_SEC,
    outline = BORDER,
    outlineVariant = BORDER_LIGHT,
    error = DANGER,
    errorContainer = DANGER_SOFT,
    onError = Color.White,
    onErrorContainer = DANGER
)

// Wraps the entire app in MainActivity so every screen uses our custom colors and fonts
@Composable
fun FileOrganizerTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = ColorScheme,
        typography = Typography,
        content = content
    )
}
