package org.openpm.engine

import kotlinx.serialization.Serializable

/** Mirrors PMI's reporting bands. Thresholds are this app's estimate: PMI does not publish its cut score. */
@Serializable
enum class Band(val label: String) {
    ABOVE_TARGET("Above Target"),
    TARGET("Target"),
    BELOW_TARGET("Below Target"),
    NEEDS_IMPROVEMENT("Needs Improvement");

    companion object {
        fun of(pct: Double): Band = when {
            pct >= 80.0 -> ABOVE_TARGET
            pct >= 65.0 -> TARGET
            pct >= 50.0 -> BELOW_TARGET
            else -> NEEDS_IMPROVEMENT
        }
    }
}

@Serializable
data class Tally(val correct: Int, val total: Int) {
    val pct: Double get() = if (total == 0) 0.0 else correct * 100.0 / total
    val band: Band get() = Band.of(pct)
}

@Serializable
data class ResultSummary(
    val total: Int,
    val correct: Int,
    val unanswered: Int,
    val byDomain: Map<Domain, Tally>,
    val byApproach: Map<Approach, Tally>,
    val byTask: Map<String, Tally>,
    val timeUsedMs: Long,
    val autoSubmitted: Boolean,
) {
    val pct: Double get() = if (total == 0) 0.0 else correct * 100.0 / total
    val band: Band get() = Band.of(pct)

    /** Tasks below 65% with at least 2 items, weakest first. */
    fun weakTasks(limit: Int = 5): List<Pair<String, Tally>> =
        byTask.entries.filter { it.value.total >= 2 && it.value.pct < 65.0 }
            .sortedBy { it.value.pct }.take(limit).map { it.key to it.value }
}

object Results {
    fun compute(s: ExamState, bank: Map<String, Question>): ResultSummary {
        val qs = s.allQuestionIds.mapNotNull { bank[it] }
        fun <K> tally(key: (Question) -> K): Map<K, Tally> =
            qs.groupBy(key).mapValues { (_, list) ->
                Tally(list.count { Scoring.isCorrect(it, s.responses[it.id]) }, list.size)
            }
        val correct = qs.count { Scoring.isCorrect(it, s.responses[it.id]) }
        val unanswered = qs.count { !Scoring.isAnswered(it, s.responses[it.id]) }
        return ResultSummary(
            total = qs.size,
            correct = correct,
            unanswered = unanswered,
            byDomain = tally { it.domain },
            byApproach = tally { it.approach },
            byTask = tally { it.taskId },
            timeUsedMs = s.timeSpentMs.values.sum(),
            autoSubmitted = s.autoSubmitted,
        )
    }
}

/**
 * Readiness guide (0–100). Never presented as a pass prediction.
 * 25% lesson coverage + 15% flashcard retention + 25% recent practice accuracy + 35% recent full-mock average.
 */
object Readiness {
    fun score(
        lessonCoverage: Double,      // 0..1
        flashcardRetention: Double,  // 0..1
        practiceAccuracy: Double?,   // 0..1, null if none
        mockAverage: Double?,        // 0..1, null if none
    ): Int {
        val v = 0.25 * lessonCoverage.coerceIn(0.0, 1.0) +
            0.15 * flashcardRetention.coerceIn(0.0, 1.0) +
            0.25 * (practiceAccuracy ?: 0.0).coerceIn(0.0, 1.0) +
            0.35 * (mockAverage ?: 0.0).coerceIn(0.0, 1.0)
        return Math.round(v * 100).toInt()
    }
}

/** SM-2 spaced repetition for flashcards. */
@Serializable
data class CardSchedule(val ease: Double = 2.5, val intervalDays: Int = 0, val repetitions: Int = 0, val dueEpochDay: Long = 0)

object Sm2 {
    /** quality: 5 = knew it, 3 = hard, 1 = again. */
    fun review(c: CardSchedule, quality: Int, todayEpochDay: Long): CardSchedule {
        val q = quality.coerceIn(0, 5)
        if (q < 3) return c.copy(repetitions = 0, intervalDays = 1, dueEpochDay = todayEpochDay + 1)
        val reps = c.repetitions + 1
        val interval = when (reps) {
            1 -> 1
            2 -> 6
            else -> Math.round(c.intervalDays * c.ease).toInt()
        }
        val ease = (c.ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))).coerceAtLeast(1.3)
        return CardSchedule(ease, interval, reps, todayEpochDay + interval)
    }
}
