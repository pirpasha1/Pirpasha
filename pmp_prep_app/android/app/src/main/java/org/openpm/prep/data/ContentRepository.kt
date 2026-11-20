package org.openpm.prep.data

import android.content.Context
import org.openpm.engine.CaseStudy
import org.openpm.engine.ContentBundle
import org.openpm.engine.Domain
import org.openpm.engine.Question

/**
 * Read-only learning content bundled in the APK (works offline, including guest mode).
 * When the optional backend is configured, newer published content replaces this bundle (see RemoteContentSource).
 */
class ContentRepository(context: Context) {
    val bundle: ContentBundle = context.assets.open("content.json").bufferedReader().use { ContentBundle.parse(it.readText()) }
    val questions: Map<String, Question> = bundle.questions.associateBy { it.id }
    val cases: Map<String, CaseStudy> = bundle.cases.associateBy { it.id }
    val tasksById = bundle.tasks.associateBy { it.id }
    val lessonsById = bundle.lessons.associateBy { it.id }

    fun tasksOf(d: Domain) = bundle.tasks.filter { it.domain == d }.sortedBy { it.number }
    fun lessonsOf(taskId: String) = bundle.lessons.filter { it.taskId == taskId }
    fun lessonsOf(d: Domain) = bundle.lessons.filter { tasksById[it.taskId]?.domain == d }
    fun cardsOf(d: Domain?) = bundle.flashcards.filter { d == null || tasksById[it.taskId]?.domain == d }
    fun taskTitle(id: String) = tasksById[id]?.let { "${it.domain.title} · Task ${it.number}: ${it.title}" } ?: id
}
