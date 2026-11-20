package org.openpm.engine

import kotlinx.serialization.Serializable

/** ECO version this build's content targets (PMI PMP Exam Content Outline, July 2026 update). */
const val CURRENT_ECO = "ECO-2026-07"

@Serializable
enum class Domain(val title: String, val weightPct: Int) {
    PEOPLE("People", 33),
    PROCESS("Process", 41),
    BUSINESS_ENV("Business Environment", 26),
}

@Serializable
enum class Approach { PREDICTIVE, AGILE, HYBRID }

@Serializable
enum class QuestionType(val label: String) {
    MCQ_SINGLE("Multiple choice"),
    MCQ_MULTI("Multiple response"),
    MATCHING("Matching"),
    DRAG_ORDER("Drag & drop – order"),
    DRAG_CATEGORIZE("Drag & drop – categorize"),
}

/** DEMO = written during development, not yet SME-reviewed. ORIGINAL_REVIEWED = approved by a PMP-certified reviewer. */
@Serializable
enum class ContentLabel { DEMO, ORIGINAL_REVIEWED }

@Serializable
data class Choice(val key: String, val text: String)

@Serializable
data class EcoTask(
    val id: String,          // e.g. "PEOPLE-T1"
    val domain: Domain,
    val number: Int,
    val title: String,
    val eco: String = CURRENT_ECO,
)

/** A case study groups several sub-questions that share one scenario (PMI "case/scenario" & practicum style). */
@Serializable
data class CaseStudy(
    val id: String,
    val title: String,
    val body: String,
    val exhibits: List<String> = emptyList(),
)

@Serializable
data class Question(
    val id: String,
    val type: QuestionType,
    val domain: Domain,
    val taskId: String,
    val approach: Approach,
    val difficulty: Int = 2,
    /** Free tags such as "scenario", "situational", "ai", "sustainability". */
    val tags: List<String> = emptyList(),
    val caseId: String? = null,
    val stem: String,
    /** MCQ options. */
    val options: List<Choice> = emptyList(),
    /** MCQ_MULTI: how many to select. */
    val selectCount: Int? = null,
    /** MATCHING: left column (prompts) and right column (answers). */
    val left: List<Choice> = emptyList(),
    val right: List<Choice> = emptyList(),
    /** DRAG_ORDER / DRAG_CATEGORIZE items. */
    val items: List<Choice> = emptyList(),
    /** DRAG_CATEGORIZE buckets. */
    val buckets: List<Choice> = emptyList(),
    /** MCQ: correct option keys. DRAG_ORDER: item keys in correct order. */
    val correct: List<String> = emptyList(),
    /** MATCHING: leftKey -> rightKey. DRAG_CATEGORIZE: itemKey -> bucketKey. */
    val pairs: Map<String, String> = emptyMap(),
    val explanation: String,
    /** Option/item key -> why it is right or wrong. */
    val rationales: Map<String, String> = emptyMap(),
    val concept: String = "",
    val label: ContentLabel = ContentLabel.DEMO,
    val eco: String = CURRENT_ECO,
    /** Options must keep authored order (e.g. "all of the above"). */
    val noShuffle: Boolean = false,
)

/** A learner's response. MCQ / order use [keys]; matching / categorize use [pairs]. */
@Serializable
data class Response(
    val keys: List<String> = emptyList(),
    val pairs: Map<String, String> = emptyMap(),
)
