package org.openpm.engine

import java.io.File
import kotlin.random.Random
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** Validates the real bundled content asset against engine rules. */
class ContentTest {
    private val bundle = ContentBundle.parse(File("../app/src/main/assets/content.json").readText())

    @Test fun bundleIsValid() {
        val problems = bundle.validate()
        assertTrue(problems.isEmpty(), problems.joinToString("\n"))
    }

    @Test fun coversEveryEcoTask() {
        assertEquals(26, bundle.tasks.size)
        assertEquals(Domain.entries.associateWith { d -> listOf(8, 10, 8)[d.ordinal] }, bundle.tasks.groupingBy { it.domain }.eachCount())
        val lessonTasks = bundle.lessons.map { it.taskId }.toSet()
        assertTrue(bundle.tasks.all { it.id in lessonTasks }, "every ECO task needs a lesson")
        assertTrue(bundle.questions.all { it.eco == CURRENT_ECO })
    }

    @Test fun allItemTypesPresent() {
        assertEquals(QuestionType.entries.toSet(), bundle.questions.map { it.type }.toSet())
        assertTrue(bundle.questions.any { it.caseId != null })
    }

    @Test fun noVerifiedPartnersInSeed() {
        assertTrue(bundle.institutions.all { it.partnership == PartnershipStatus.LISTED })
    }

    @Test fun demoExamCanBeBuiltFromBank() {
        val sel = Selector(bundle.questions, Random(4)).build(ExamBlueprint.DEMO)
        assertEquals(20, sel.sections.single().size)
        assertEquals(0, sel.shortfall)
    }
}
