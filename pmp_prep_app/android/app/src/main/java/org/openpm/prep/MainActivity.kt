package org.openpm.prep

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.staticCompositionLocalOf
import org.openpm.prep.ui.AppRoot
import org.openpm.prep.ui.theme.PrepTheme

val LocalContainer = staticCompositionLocalOf<AppContainer> { error("No container") }

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val container = (application as PrepApp).container
        setContent {
            val settings by container.settings.settings.collectAsState(initial = null)
            CompositionLocalProvider(LocalContainer provides container) {
                PrepTheme(settings?.theme, settings?.textScale ?: 1f) {
                    settings?.let { AppRoot(it) }
                }
            }
        }
    }
}

