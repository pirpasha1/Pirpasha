package org.openpm.prep.data

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import org.openpm.engine.CardSchedule
import org.openpm.engine.ContentBundle
import org.openpm.engine.Domain
import org.openpm.engine.ExamMode
import org.openpm.engine.ExamState
import org.openpm.engine.Readiness
import org.openpm.engine.ResultSummary
import org.openpm.engine.Sm2
import org.openpm.engine.Tally
import java.time.LocalDate

data class AttemptSummary(
    val id: String,
    val mode: ExamMode,
    val title: String,
    val startedAt: Long,
    val submitted: Boolean,
    val scorePct: Double?,
    val questionCount: Int,
    val result: ResultSummary?,
)

data class Dashboard(
    val studySeconds: Long,
    val lessonsDone: Int,
    val lessonsTotal: Int,
    val lastPractice: AttemptSummary?,
    val lastMock: AttemptSummary?,
    val mockTrend: List<Double>,
    val readiness: Int,
    val domainAccuracy: Map<Domain, Tally>,
    val inProgress: List<AttemptSummary>,
    val cardsDue: Int,
    val todaySeconds: Long,
    val history: List<AttemptSummary>,
    val completedLessons: Set<String>,
)

class ProgressRepository(private val dao: PrepDao, private val content: ContentRepository) {
    private val json = ContentBundle.json

    fun today(): Long = LocalDate.now().toEpochDay()

    fun attempt(id: String): Flow<AttemptSummary?> = dao.attemptFlow(id).map { it?.toSummary() }

    fun summaries(): Flow<List<AttemptSummary>> = dao.attempts().map { list -> list.map { it.toSummary() } }

    private fun AttemptEntity.toSummary() = AttemptSummary(
        id = id, mode = ExamMode.valueOf(mode), title = title, startedAt = startedAt, submitted = submittedAt != null,
        scorePct = scorePct, questionCount = questionCount,
        result = resultJson?.let { runCatching { json.decodeFromString(ResultSummary.serializer(), it) }.getOrNull() },
    )

    val dashboard: Flow<Dashboard> = combine(dao.attempts(), dao.lessonProgress(), dao.cardReviews(), dao.studyDays()) { attempts, lessons, cards, days ->
        val all = attempts.map { it.toSummary() }
        val done = all.filter { it.submitted && it.result != null }
        val practice = done.filter { it.mode != ExamMode.MOCK }
        val mocks = done.filter { it.mode == ExamMode.MOCK }
        // Practice accuracy over (roughly) the last 200 items.
        var items = 0; var correct = 0
        for (a in practice) { if (items >= 200) break; items += a.result!!.total; correct += a.result.correct }
        val practiceAcc = if (items == 0) null else correct.toDouble() / items
        val mockAvg = mocks.take(2).takeIf { it.isNotEmpty() }?.map { it.result!!.pct / 100 }?.average()
        val completed = lessons.filter { it.completedAt != null }.map { it.lessonId }.toSet()
        val lessonCoverage = completed.size.toDouble() / content.bundle.lessons.size.coerceAtLeast(1)
        val totalCards = content.bundle.flashcards.size.coerceAtLeast(1)
        val retention = cards.count { it.lastQuality >= 3 }.toDouble() / totalCards
        val today = today()
        val reviewed = cards.associateBy { it.cardId }
        val due = content.bundle.flashcards.count { c -> reviewed[c.id]?.let { it.dueEpochDay <= today } ?: true }
        val domainAcc = Domain.entries.associateWith { d ->
            done.mapNotNull { it.result?.byDomain?.get(d) }.fold(Tally(0, 0)) { acc, t -> Tally(acc.correct + t.correct, acc.total + t.total) }
        }
        Dashboard(
            studySeconds = days.sumOf { it.seconds },
            lessonsDone = completed.size,
            lessonsTotal = content.bundle.lessons.size,
            lastPractice = practice.firstOrNull(),
            lastMock = mocks.firstOrNull(),
            mockTrend = mocks.take(8).reversed().map { it.result!!.pct },
            readiness = Readiness.score(lessonCoverage, retention, practiceAcc, mockAvg),
            domainAccuracy = domainAcc,
            inProgress = all.filter { !it.submitted },
            cardsDue = due,
            todaySeconds = days.firstOrNull { it.epochDay == today }?.seconds ?: 0,
            history = done,
            completedLessons = completed,
        )
    }

    // ---- attempts
    suspend fun saveAttempt(state: ExamState, result: ResultSummary? = null) {
        dao.upsertAttempt(
            AttemptEntity(
                id = state.attemptId, mode = state.mode.name, title = state.title, startedAt = state.startedAtEpochMs,
                submittedAt = state.submittedAtEpochMs, scorePct = result?.pct, questionCount = state.allQuestionIds.size,
                stateJson = json.encodeToString(ExamState.serializer(), state),
                resultJson = result?.let { json.encodeToString(ResultSummary.serializer(), it) },
            ),
        )
    }

    suspend fun loadState(id: String): ExamState? =
        dao.attempt(id)?.let { runCatching { json.decodeFromString(ExamState.serializer(), it.stateJson) }.getOrNull() }

    suspend fun loadResult(id: String): ResultSummary? =
        dao.attempt(id)?.resultJson?.let { json.decodeFromString(ResultSummary.serializer(), it) }

    suspend fun deleteAttempt(id: String) = dao.deleteAttempt(id)

    /** Question ids from the last few attempts, so new tests prefer fresh questions. */
    suspend fun recentlySeen(): Set<String> = dao.recentStates(5).flatMap { js ->
        runCatching { json.decodeFromString(ExamState.serializer(), js).allQuestionIds }.getOrDefault(emptyList())
    }.toSet()

    // ---- study time & lessons
    suspend fun addStudySeconds(seconds: Long) {
        if (seconds <= 0) return
        val day = today()
        val cur = dao.studyDay(day)?.seconds ?: 0
        dao.upsertStudyDay(StudyDayEntity(day, cur + seconds))
    }

    suspend fun recordLessonTime(lessonId: String, seconds: Long) {
        val cur = dao.lesson(lessonId) ?: LessonProgressEntity(lessonId)
        dao.upsertLesson(cur.copy(secondsSpent = cur.secondsSpent + seconds))
        addStudySeconds(seconds)
    }

    suspend fun setLessonComplete(lessonId: String, complete: Boolean) {
        val cur = dao.lesson(lessonId) ?: LessonProgressEntity(lessonId)
        dao.upsertLesson(cur.copy(completedAt = if (complete) System.currentTimeMillis() else null))
    }

    // ---- flashcards
    fun cardReviews() = dao.cardReviews()

    suspend fun reviewCard(cardId: String, previous: CardReviewEntity?, quality: Int) {
        val prev = previous?.let { CardSchedule(it.ease, it.intervalDays, it.repetitions, it.dueEpochDay) } ?: CardSchedule()
        val next = Sm2.review(prev, quality, today())
        dao.upsertCard(CardReviewEntity(cardId, next.ease, next.intervalDays, next.repetitions, next.dueEpochDay, quality))
        addStudySeconds(15)
    }

    // ---- directory & feedback
    suspend fun saveEnquiry(e: EnquiryEntity) = dao.insertEnquiry(e)
    suspend fun saveFeedback(questionId: String?, kind: String, message: String) =
        dao.insertFeedback(FeedbackEntity(questionId = questionId, kind = kind, message = message, createdAt = System.currentTimeMillis()))

    suspend fun resetAll() {
        dao.clearAttempts(); dao.clearLessons(); dao.clearCards(); dao.clearDays(); dao.clearEnquiries(); dao.clearFeedback()
    }
}
