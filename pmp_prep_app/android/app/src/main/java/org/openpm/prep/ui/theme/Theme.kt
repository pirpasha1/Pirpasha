package org.openpm.prep.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density
import org.openpm.prep.data.ThemeMode

// Calm navy + teal, amber for "marked for review".
val Amber = Color(0xFFF59E0B)
val Success = Color(0xFF15803D)
val SuccessDark = Color(0xFF4ADE80)
val Danger = Color(0xFFB91C1C)
val DangerDark = Color(0xFFF87171)

private val Light = lightColorScheme(
    primary = Color(0xFF0F3D5E), onPrimary = Color.White,
    primaryContainer = Color(0xFFD3E5F5), onPrimaryContainer = Color(0xFF0A2940),
    secondary = Color(0xFF0D9488), onSecondary = Color.White,
    secondaryContainer = Color(0xFFCCF2EE), onSecondaryContainer = Color(0xFF053B36),
    tertiary = Color(0xFFB45309), tertiaryContainer = Color(0xFFFDE8C8), onTertiaryContainer = Color(0xFF4A2300),
    background = Color(0xFFF7F9FC), surface = Color(0xFFFFFFFF), surfaceVariant = Color(0xFFE6ECF2),
    onSurface = Color(0xFF14202B), onSurfaceVariant = Color(0xFF45525E), outline = Color(0xFF8995A1),
    error = Danger,
)

private val Dark = darkColorScheme(
    primary = Color(0xFF9CC8EC), onPrimary = Color(0xFF07263C),
    primaryContainer = Color(0xFF1C4867), onPrimaryContainer = Color(0xFFD3E5F5),
    secondary = Color(0xFF5EEAD4), onSecondary = Color(0xFF00352F),
    secondaryContainer = Color(0xFF0F4C46), onSecondaryContainer = Color(0xFFCCF2EE),
    tertiary = Color(0xFFFBBF24), tertiaryContainer = Color(0xFF5C3A08), onTertiaryContainer = Color(0xFFFDE8C8),
    background = Color(0xFF0E141A), surface = Color(0xFF151D25), surfaceVariant = Color(0xFF24303B),
    onSurface = Color(0xFFE4EAF0), onSurfaceVariant = Color(0xFFB4C0CB), outline = Color(0xFF7D8994),
    error = DangerDark,
)

@Composable
fun isDark(mode: ThemeMode?) = when (mode) {
    ThemeMode.LIGHT -> false
    ThemeMode.DARK -> true
    else -> isSystemInDarkTheme()
}

@Composable
fun PrepTheme(mode: ThemeMode?, textScale: Float = 1f, content: @Composable () -> Unit) {
    val dark = isDark(mode)
    val density = LocalDensity.current
    CompositionLocalProvider(LocalDensity provides Density(density.density, density.fontScale * textScale)) {
        MaterialTheme(colorScheme = if (dark) Dark else Light, typography = Typography(), content = content)
    }
}

@Composable
fun okColor() = if (MaterialTheme.colorScheme.background.red < 0.5f) SuccessDark else Success

@Composable
fun badColor() = MaterialTheme.colorScheme.error
