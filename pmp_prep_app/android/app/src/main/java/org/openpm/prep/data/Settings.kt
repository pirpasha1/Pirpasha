package org.openpm.prep.data

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

enum class ThemeMode { SYSTEM, LIGHT, DARK }

data class Settings(
    val onboarded: Boolean = false,
    val displayName: String = "",
    val theme: ThemeMode = ThemeMode.SYSTEM,
    /** Exam date as epoch day, or null. */
    val examEpochDay: Long? = null,
    val dailyGoalMin: Int = 30,
    val textScale: Float = 1f,
    val lastLessonId: String? = null,
)

private val Context.store by preferencesDataStore("settings")

class SettingsStore(private val context: Context) {
    private object K {
        val onboarded = booleanPreferencesKey("onboarded")
        val name = stringPreferencesKey("name")
        val theme = stringPreferencesKey("theme")
        val exam = longPreferencesKey("exam_day")
        val goal = intPreferencesKey("goal")
        val scale = stringPreferencesKey("text_scale")
        val lastLesson = stringPreferencesKey("last_lesson")
    }

    val settings: Flow<Settings> = context.store.data.map { p -> p.toSettings() }

    private fun Preferences.toSettings() = Settings(
        onboarded = this[K.onboarded] ?: false,
        displayName = this[K.name] ?: "",
        theme = runCatching { ThemeMode.valueOf(this[K.theme] ?: "SYSTEM") }.getOrDefault(ThemeMode.SYSTEM),
        examEpochDay = this[K.exam],
        dailyGoalMin = this[K.goal] ?: 30,
        textScale = this[K.scale]?.toFloatOrNull() ?: 1f,
        lastLessonId = this[K.lastLesson],
    )

    suspend fun completeOnboarding(name: String) = context.store.edit { it[K.onboarded] = true; it[K.name] = name.trim() }
    suspend fun setName(name: String) = context.store.edit { it[K.name] = name.trim() }
    suspend fun setTheme(t: ThemeMode) = context.store.edit { it[K.theme] = t.name }
    suspend fun setExamDay(day: Long?) = context.store.edit { if (day == null) it.remove(K.exam) else it[K.exam] = day }
    suspend fun setGoal(min: Int) = context.store.edit { it[K.goal] = min }
    suspend fun setTextScale(s: Float) = context.store.edit { it[K.scale] = s.toString() }
    suspend fun setLastLesson(id: String) = context.store.edit { it[K.lastLesson] = id }
    suspend fun clear() = context.store.edit { it.clear() }
}
