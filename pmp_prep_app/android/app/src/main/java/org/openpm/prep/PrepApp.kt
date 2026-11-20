package org.openpm.prep

import android.app.Application
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import org.openpm.prep.data.ContentRepository
import org.openpm.prep.data.PrepDatabase
import org.openpm.prep.data.ProgressRepository
import org.openpm.prep.data.SettingsStore

/** Manual dependency container (small app; avoids DI framework overhead). */
class AppContainer(app: Application) {
    val content by lazy { ContentRepository(app) }
    val db by lazy { PrepDatabase.build(app) }
    val progress by lazy { ProgressRepository(db.dao(), content) }
    val settings by lazy { SettingsStore(app) }
    /** Outlives screens: used for saves that must finish after a screen closes. */
    val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
}

class PrepApp : Application() {
    lateinit var container: AppContainer
    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}
