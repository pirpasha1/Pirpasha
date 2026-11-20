package org.openpm.engine

import kotlinx.serialization.Serializable

@Serializable
enum class ExamMode { PRACTICE, DEMO, MOCK }

@Serializable
enum class Phase { IN_SECTION, ON_BREAK, SUBMITTED }

@Serializable
data class SectionState(
    val name: String,
    val questionIds: List<String>,
    val breakAfter: Boolean,
)

/**
 * Complete, serializable state of one attempt. It is persisted after every change,
 * so an attempt survives process death, phone calls and reboots.
 * The exam clock does not run during breaks (breaks are outside the 240 minutes).
 */
@Serializable
data class ExamState(
    val attemptId: String,
    val mode: ExamMode,
    val title: String,
    val blueprintId: String,
    val sections: List<SectionState>,
    val instantFeedback: Boolean = false,
    val currentSection: Int = 0,
    val currentIndex: Int = 0,
    val responses: Map<String, Response> = emptyMap(),
    val marked: Set<String> = emptySet(),
    /** Questions whose instant feedback was revealed (answer locked). */
    val revealed: Set<String> = emptySet(),
    val timeRemainingMs: Long,
    /** Total exam time at start, used e.g. to decide which time warnings apply. */
    val durationMs: Long = 0,
    val breakMinutes: Int = 10,
    val breakRemainingMs: Long = 0,
    val phase: Phase = Phase.IN_SECTION,
    val autoSubmitted: Boolean = false,
    val startedAtEpochMs: Long,
    val submittedAtEpochMs: Long? = null,
    val timeSpentMs: Map<String, Long> = emptyMap(),
    val shortfall: Int = 0,
) {
    val section: SectionState get() = sections[currentSection]
    val currentQuestionId: String get() = section.questionIds[currentIndex]
    val allQuestionIds: List<String> get() = sections.flatMap { it.questionIds }
    val isLastSection: Boolean get() = currentSection == sections.lastIndex
    /** 1-based overall number of the current question. */
    val overallNumber: Int get() = sections.take(currentSection).sumOf { it.questionIds.size } + currentIndex + 1
}

/** Pure state transitions. Callers persist the returned state. */
object ExamEngine {

    fun start(
        attemptId: String,
        mode: ExamMode,
        blueprint: ExamBlueprint,
        selection: Selection,
        nowEpochMs: Long,
        instantFeedback: Boolean = false,
    ): ExamState {
        val sections = blueprint.sections.mapIndexed { i, spec ->
            SectionState(spec.name, selection.sections[i], spec.breakAfter)
        }.filter { it.questionIds.isNotEmpty() }
        require(sections.isNotEmpty()) { "Question bank has no questions for this exam" }
        // Do not offer a break after what has become the final section.
        val fixed = sections.mapIndexed { i, s -> if (i == sections.lastIndex) s.copy(breakAfter = false) else s }
        val total = fixed.sumOf { it.questionIds.size }
        // Scale time if the bank could not fill the blueprint, keeping the real pace.
        val fullCount = blueprint.totalQuestions
        val durationMs = blueprint.durationMin * 60_000L * total / fullCount
        return ExamState(
            attemptId = attemptId,
            mode = mode,
            title = blueprint.name,
            blueprintId = blueprint.id,
            sections = fixed,
            instantFeedback = instantFeedback && mode == ExamMode.PRACTICE,
            timeRemainingMs = durationMs,
            durationMs = durationMs,
            breakMinutes = blueprint.breakMin,
            startedAtEpochMs = nowEpochMs,
            shortfall = selection.shortfall,
        )
    }

    fun answer(s: ExamState, questionId: String, r: Response): ExamState {
        if (s.phase != Phase.IN_SECTION || questionId in s.revealed) return s
        if (questionId !in s.section.questionIds) return s
        return s.copy(responses = s.responses + (questionId to r))
    }

    fun reveal(s: ExamState, questionId: String): ExamState =
        if (!s.instantFeedback) s else s.copy(revealed = s.revealed + questionId)

    fun toggleMark(s: ExamState, questionId: String): ExamState =
        s.copy(marked = if (questionId in s.marked) s.marked - questionId else s.marked + questionId)

    fun goTo(s: ExamState, index: Int): ExamState =
        if (s.phase != Phase.IN_SECTION || index !in s.section.questionIds.indices) s else s.copy(currentIndex = index)

    fun next(s: ExamState) = goTo(s, s.currentIndex + 1)
    fun prev(s: ExamState) = goTo(s, s.currentIndex - 1)

    /**
     * Advance the clock by [elapsedMs] (measured by the caller with a monotonic clock).
     * Time spent is attributed to the current question. Expiry auto-submits.
     */
    fun tick(s: ExamState, elapsedMs: Long, nowEpochMs: Long): ExamState {
        if (elapsedMs <= 0) return s
        return when (s.phase) {
            Phase.SUBMITTED -> s
            Phase.ON_BREAK -> {
                val left = s.breakRemainingMs - elapsedMs
                if (left <= 0) endBreak(s) else s.copy(breakRemainingMs = left)
            }
            Phase.IN_SECTION -> {
                val qid = s.currentQuestionId
                val spent = s.timeSpentMs + (qid to ((s.timeSpentMs[qid] ?: 0L) + elapsedMs))
                val left = s.timeRemainingMs - elapsedMs
                if (left <= 0) submit(s.copy(timeRemainingMs = 0, timeSpentMs = spent), nowEpochMs, auto = true)
                else s.copy(timeRemainingMs = left, timeSpentMs = spent)
            }
        }
    }

    /**
     * Leave the current section. If a break follows, the section locks and the break starts;
     * on the last section this is not allowed — use [submit].
     */
    fun finishSection(s: ExamState): ExamState {
        if (s.phase != Phase.IN_SECTION || s.isLastSection) return s
        return if (s.section.breakAfter) {
            s.copy(phase = Phase.ON_BREAK, breakRemainingMs = s.breakMinutes * 60_000L)
        } else {
            s.copy(currentSection = s.currentSection + 1, currentIndex = 0)
        }
    }

    /** End the break (early or on time) and start the next section. */
    fun endBreak(s: ExamState): ExamState {
        if (s.phase != Phase.ON_BREAK) return s
        return s.copy(phase = Phase.IN_SECTION, breakRemainingMs = 0, currentSection = s.currentSection + 1, currentIndex = 0)
    }

    fun submit(s: ExamState, nowEpochMs: Long, auto: Boolean = false): ExamState =
        if (s.phase == Phase.SUBMITTED) s
        else s.copy(phase = Phase.SUBMITTED, autoSubmitted = auto, submittedAtEpochMs = nowEpochMs)

    fun unansweredInSection(s: ExamState, bank: Map<String, Question>): Int =
        s.section.questionIds.count { !Scoring.isAnswered(bank.getValue(it), s.responses[it]) }

    fun markedInSection(s: ExamState): Int = s.section.questionIds.count { it in s.marked }
}
