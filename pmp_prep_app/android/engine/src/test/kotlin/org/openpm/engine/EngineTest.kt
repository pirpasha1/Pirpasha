package org.openpm.engine

import kotlin.random.Random
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class ScoringTest {
    private val single = Question(
        id = "s", type = QuestionType.MCQ_SINGLE, domain = Domain.PEOPLE, taskId = "PEOPLE-T1",
        approach = Approach.AGILE, stem = "?", explanation = "e",
        options = listOf(Choice("A", "a"), Choice("B", "b"), Choice("C", "c")), correct = listOf("B"),
    )
    private val multi = single.copy(
        id = "m", type = QuestionType.MCQ_MULTI, selectCount = 2,
        options = single.options + Choice("D", "d"), correct = listOf("A", "C"),
    )
    private val order = single.copy(
        id = "o", type = QuestionType.DRAG_ORDER, options = emptyList(),
        items = listOf(Choice("1", "x"), Choice("2", "y"), Choice("3", "z")), correct = listOf("2", "1", "3"),
    )
    private val match = single.copy(
        id = "mt", type = QuestionType.MATCHING, options = emptyList(), correct = emptyList(),
        left = listOf(Choice("L1", "l1"), Choice("L2", "l2")), right = listOf(Choice("R1", "r1"), Choice("R2", "r2"), Choice("R3", "r3")),
        pairs = mapOf("L1" to "R2", "L2" to "R1"),
    )
    private val cat = single.copy(
        id = "c", type = QuestionType.DRAG_CATEGORIZE, options = emptyList(), correct = emptyList(),
        items = listOf(Choice("i1", "a"), Choice("i2", "b")), buckets = listOf(Choice("b1", "B1"), Choice("b2", "B2")),
        pairs = mapOf("i1" to "b2", "i2" to "b1"),
    )

    @Test fun singleChoice() {
        assertTrue(Scoring.isCorrect(single, Response(listOf("B"))))
        assertFalse(Scoring.isCorrect(single, Response(listOf("A"))))
        assertFalse(Scoring.isCorrect(single, null))
        assertFalse(Scoring.isAnswered(single, Response()))
    }

    @Test fun multiResponseIsAllOrNothing() {
        assertTrue(Scoring.isCorrect(multi, Response(listOf("C", "A"))))
        assertFalse(Scoring.isCorrect(multi, Response(listOf("A"))))
        assertFalse(Scoring.isCorrect(multi, Response(listOf("A", "C", "D"))))
        assertEquals(1 to 2, Scoring.partialHits(multi, Response(listOf("A", "D"))))
    }

    @Test fun dragOrder() {
        assertTrue(Scoring.isCorrect(order, Response(listOf("2", "1", "3"))))
        assertFalse(Scoring.isCorrect(order, Response(listOf("1", "2", "3"))))
        assertFalse(Scoring.isAnswered(order, Response(listOf("1"))))
    }

    @Test fun matchingAndCategorize() {
        assertTrue(Scoring.isCorrect(match, Response(pairs = mapOf("L1" to "R2", "L2" to "R1"))))
        assertFalse(Scoring.isCorrect(match, Response(pairs = mapOf("L1" to "R2", "L2" to "R3"))))
        assertFalse(Scoring.isAnswered(match, Response(pairs = mapOf("L1" to "R2"))))
        assertTrue(Scoring.isCorrect(cat, Response(pairs = mapOf("i1" to "b2", "i2" to "b1"))))
        assertFalse(Scoring.isCorrect(cat, Response(pairs = mapOf("i1" to "b1", "i2" to "b1"))))
    }

    @Test fun validationCatchesBadContent() {
        assertTrue(Scoring.validate(single).isEmpty())
        assertTrue(Scoring.validate(multi).isEmpty())
        assertTrue(Scoring.validate(order).isEmpty())
        assertTrue(Scoring.validate(match).isEmpty())
        assertTrue(Scoring.validate(cat).isEmpty())
        assertTrue(Scoring.validate(single.copy(correct = listOf("Z"))).isNotEmpty())
        assertTrue(Scoring.validate(cat.copy(pairs = mapOf("i1" to "b1"))).isNotEmpty())
    }
}

class SelectorTest {
    private fun bank(n: Int): List<Question> = (0 until n).map { i ->
        val d = Domain.entries[i % 3]
        Question(
            id = "q$i", type = QuestionType.MCQ_SINGLE, domain = d, taskId = "${d.name}-T1",
            approach = if (i % 5 < 2) Approach.PREDICTIVE else Approach.AGILE, stem = "?", explanation = "e",
            options = listOf(Choice("A", "a"), Choice("B", "b"), Choice("C", "c")), correct = listOf("A"),
        )
    }

    @Test fun apportionSumsToTotal() {
        val m = Selector.apportion(180, Domain.entries.associateWith { it.weightPct })
        assertEquals(180, m.values.sum())
        assertEquals(59, m[Domain.PEOPLE]); assertEquals(74, m[Domain.PROCESS]); assertEquals(47, m[Domain.BUSINESS_ENV])
    }

    @Test fun practiceSelectionFollowsDomainWeights() {
        val sel = Selector(bank(600), Random(1)).build(ExamBlueprint.practice(60))
        val ids = sel.sections.single()
        assertEquals(60, ids.size); assertEquals(60, ids.toSet().size); assertEquals(0, sel.shortfall)
        val b = bank(600).associateBy { it.id }
        val byDomain = ids.groupingBy { b.getValue(it).domain }.eachCount()
        assertEquals(20, byDomain[Domain.PEOPLE]); assertEquals(25, byDomain[Domain.PROCESS]); assertEquals(15, byDomain[Domain.BUSINESS_ENV])
    }

    @Test fun shortBankReportsShortfall() {
        val sel = Selector(bank(12), Random(1)).build(ExamBlueprint.practice(30))
        assertEquals(12, sel.sections.single().size); assertEquals(18, sel.shortfall)
    }

    @Test fun domainFilter() {
        val b = bank(90)
        val sel = Selector(b, Random(2)).build(ExamBlueprint.practice(10), domainFilter = setOf(Domain.PROCESS))
        val m = b.associateBy { it.id }
        assertTrue(sel.sections.single().all { m.getValue(it).domain == Domain.PROCESS })
    }

    @Test fun caseSectionTakesWholeCases() {
        val b = bank(300) + (0 until 6).flatMap { c -> (0 until 5).map { k -> bank(1)[0].copy(id = "case$c-$k", caseId = "case$c") } }
        val sel = Selector(b, Random(3)).build(ExamBlueprint.PMP_2026_FULL)
        val first = sel.sections[0]
        assertEquals(30, first.size)
        assertTrue(first.all { it.startsWith("case") })
        // Fewer case items than the section size: no standalone top-up, gap reported.
        val small = b.filter { !(it.caseId != null && it.caseId!! > "case0") }
        val sel2 = Selector(small, Random(3)).build(ExamBlueprint.PMP_2026_FULL)
        assertEquals(5, sel2.sections[0].size); assertTrue(sel2.sections[0].all { it.startsWith("case") }); assertEquals(25, sel2.shortfall)
        assertEquals(180, sel.sections.sumOf { it.size }); assertEquals(180, sel.sections.flatten().toSet().size)
    }
}

class ExamEngineTest {
    private val b =
        (0 until 300).map { i ->
            Question(
                id = "q$i", type = QuestionType.MCQ_SINGLE, domain = Domain.entries[i % 3], taskId = "x",
                approach = Approach.AGILE, stem = "?", explanation = "e",
                options = listOf(Choice("A", "a"), Choice("B", "b"), Choice("C", "c")), correct = listOf("A"),
            )
        }
    private val bank = b.associateBy { it.id }

    private fun fullExam(): ExamState {
        val bp = ExamBlueprint.PMP_2026_FULL.copy(sections = ExamBlueprint.PMP_2026_FULL.sections.map { it.copy(caseStudy = false) })
        return ExamEngine.start("a1", ExamMode.MOCK, bp, Selector(b, Random(5)).build(bp), nowEpochMs = 0)
    }

    @Test fun fullMockUses240Minutes() {
        val s = fullExam()
        assertEquals(240 * 60_000L, s.timeRemainingMs)
        assertEquals(3, s.sections.size); assertEquals(180, s.allQuestionIds.size)
    }

    @Test fun autoSubmitOnTimeout() {
        var s = fullExam()
        s = ExamEngine.tick(s, 239 * 60_000L, 1)
        assertEquals(Phase.IN_SECTION, s.phase)
        s = ExamEngine.tick(s, 61_000L, 2)
        assertEquals(Phase.SUBMITTED, s.phase); assertTrue(s.autoSubmitted); assertEquals(0, s.timeRemainingMs)
    }

    @Test fun breakLocksSectionAndPausesExamClock() {
        var s = fullExam()
        val firstSectionQ = s.currentQuestionId
        s = ExamEngine.finishSection(s)
        assertEquals(Phase.ON_BREAK, s.phase)
        val before = s.timeRemainingMs
        s = ExamEngine.tick(s, 5 * 60_000L, 1)
        assertEquals(before, s.timeRemainingMs)
        // Answers to the locked section are ignored after the break.
        s = ExamEngine.tick(s, 5 * 60_000L, 2)
        assertEquals(Phase.IN_SECTION, s.phase); assertEquals(1, s.currentSection)
        s = ExamEngine.answer(s, firstSectionQ, Response(listOf("A")))
        assertFalse(firstSectionQ in s.responses)
    }

    @Test fun lastSectionCannotBeFinishedOnlySubmitted() {
        var s = fullExam()
        s = ExamEngine.endBreak(ExamEngine.finishSection(s))
        s = ExamEngine.endBreak(ExamEngine.finishSection(s))
        assertEquals(2, s.currentSection)
        assertEquals(s, ExamEngine.finishSection(s))
        s = ExamEngine.submit(s, 9)
        assertEquals(Phase.SUBMITTED, s.phase); assertFalse(s.autoSubmitted)
    }

    @Test fun navigationMarkingAndResults() {
        val bp = ExamBlueprint.practice(10)
        var s = ExamEngine.start("p", ExamMode.PRACTICE, bp, Selector(b, Random(9)).build(bp), 0, instantFeedback = true)
        assertEquals(14 * 60_000L, s.timeRemainingMs) // 10 x 80 s rounded up to 14 min
        s = ExamEngine.answer(s, s.currentQuestionId, Response(listOf("A")))
        s = ExamEngine.toggleMark(s, s.currentQuestionId)
        s = ExamEngine.reveal(s, s.currentQuestionId)
        val locked = ExamEngine.answer(s, s.currentQuestionId, Response(listOf("B")))
        assertEquals(listOf("A"), locked.responses[s.currentQuestionId]!!.keys)
        s = ExamEngine.next(s); s = ExamEngine.answer(s, s.currentQuestionId, Response(listOf("B")))
        s = ExamEngine.prev(s); assertEquals(0, s.currentIndex)
        s = ExamEngine.goTo(s, 99); assertEquals(0, s.currentIndex)
        s = ExamEngine.tick(s, 30_000, 1)
        s = ExamEngine.submit(s, 2)
        val r = Results.compute(s, bank)
        assertEquals(10, r.total); assertEquals(1, r.correct); assertEquals(8, r.unanswered)
        assertEquals(10.0, r.pct); assertEquals(Band.NEEDS_IMPROVEMENT, r.band); assertEquals(30_000, r.timeUsedMs)
        assertEquals(1, ExamEngine.markedInSection(s))
    }

    @Test fun stateSurvivesSerialization() {
        val s = ExamEngine.toggleMark(fullExam(), "q1")
        val json = ContentBundle.json.encodeToString(ExamState.serializer(), s)
        assertEquals(s, ContentBundle.json.decodeFromString(ExamState.serializer(), json))
    }
}

class ReadinessAndSm2Test {
    @Test fun readinessWeights() {
        assertEquals(0, Readiness.score(0.0, 0.0, null, null))
        assertEquals(100, Readiness.score(1.0, 1.0, 1.0, 1.0))
        assertEquals(59, Readiness.score(1.0, 0.0, 0.8, 0.4)) // 25 + 0 + 20 + 14
    }

    @Test fun sm2Intervals() {
        var c = CardSchedule()
        c = Sm2.review(c, 5, 100); assertEquals(1, c.intervalDays); assertEquals(101, c.dueEpochDay)
        c = Sm2.review(c, 5, 101); assertEquals(6, c.intervalDays)
        c = Sm2.review(c, 5, 107); assertTrue(c.intervalDays >= 15)
        c = Sm2.review(c, 1, 120); assertEquals(1, c.intervalDays); assertEquals(0, c.repetitions)
    }
}
