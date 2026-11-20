package org.openpm.engine

import kotlinx.serialization.Serializable

@Serializable
data class SectionSpec(
    val name: String,
    val questionCount: Int,
    /** Section is filled with whole case studies first. */
    val caseStudy: Boolean = false,
    /** A break may be taken after this section; the section locks once left. */
    val breakAfter: Boolean = false,
)

/**
 * Exam format as data, so new PMI formats need no app release.
 * Section sizes inside the full 2026 mock are an assumption: PMI publishes the
 * 180 questions / 240 minutes / 2 breaks rule but not the case-study section size.
 */
@Serializable
data class ExamBlueprint(
    val id: String,
    val name: String,
    val eco: String,
    val durationMin: Int,
    val sections: List<SectionSpec>,
    val breakMin: Int = 10,
    val domainMix: Map<Domain, Int> = Domain.entries.associateWith { it.weightPct },
    /** Share of predictive items; the rest are agile or hybrid. */
    val predictivePct: Int = 40,
) {
    val totalQuestions: Int get() = sections.sumOf { it.questionCount }

    companion object {
        val PMP_2026_FULL = ExamBlueprint(
            id = "pmp-2026-full",
            name = "Full PMP mock (July 2026 format)",
            eco = CURRENT_ECO,
            durationMin = 240,
            sections = listOf(
                SectionSpec("Case studies", 30, caseStudy = true, breakAfter = true),
                SectionSpec("Independent questions – part A", 75, breakAfter = true),
                SectionSpec("Independent questions – part B", 75),
            ),
        )

        val DEMO = ExamBlueprint(
            id = "pmp-2026-demo",
            name = "Short demo exam",
            eco = CURRENT_ECO,
            durationMin = 25,
            sections = listOf(SectionSpec("Demo", 20)),
        )

        /** Practice tests use the real exam pace: 240 min / 180 q = 80 s per question. */
        fun practice(count: Int) = ExamBlueprint(
            id = "practice-$count",
            name = "$count-question practice test",
            eco = CURRENT_ECO,
            durationMin = maxOf(1, (count * 80 + 59) / 60),
            sections = listOf(SectionSpec("Practice", count)),
        )
    }
}
