package org.openpm.engine

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

@Serializable
data class Term(val term: String, val definition: String)

@Serializable
data class Lesson(
    val id: String,
    val taskId: String,
    val title: String,
    val summary: String,
    /** Paragraphs; lines starting with "- " render as bullets. */
    val body: List<String>,
    val keyTerms: List<Term> = emptyList(),
    val example: String = "",
    val approachNote: String = "",
    val examTip: String = "",
    val minutes: Int = 8,
    val label: ContentLabel = ContentLabel.DEMO,
    val eco: String = CURRENT_ECO,
)

@Serializable
data class Flashcard(val id: String, val taskId: String, val front: String, val back: String)

@Serializable
data class Faq(val id: String, val question: String, val answer: String)

@Serializable
enum class ResourceCategory(val title: String) {
    OFFICIAL("PMI official (public)"),
    GUIDE("Free guides"),
    VIDEO("Videos & courses"),
    WEBINAR("Webinars & events"),
    ARTICLE("Articles"),
    SAMPLE_QUESTIONS("Sample questions"),
    OER("Open educational resources"),
}

@Serializable
data class Resource(
    val id: String,
    val category: ResourceCategory,
    val title: String,
    val provider: String,
    val url: String,
    /** e.g. "Free", "Free with registration". */
    val cost: String,
    val licence: String = "Linked only – owned by provider",
    val description: String,
    /** ISO date the link and cost were last checked by an admin. */
    val lastVerified: String,
)

@Serializable
enum class PartnershipStatus(val badge: String) {
    LISTED("Listed – not a partner"),
    IN_DISCUSSION("In discussion – not a partner"),
    VERIFIED_PARTNER("Verified partner"),
}

@Serializable
data class Institution(
    val id: String,
    val name: String,
    val type: String,
    val country: String,
    val website: String,
    val description: String,
    val freeOfferings: List<String> = emptyList(),
    val partnership: PartnershipStatus = PartnershipStatus.LISTED,
)

@Serializable
data class ContentBundle(
    val eco: String,
    val contentVersion: Int,
    val tasks: List<EcoTask>,
    val lessons: List<Lesson>,
    val flashcards: List<Flashcard>,
    val faqs: List<Faq>,
    val revision: List<Term> = emptyList(),
    val cases: List<CaseStudy>,
    val questions: List<Question>,
    val resources: List<Resource>,
    val institutions: List<Institution>,
) {
    fun validate(): List<String> {
        val p = mutableListOf<String>()
        val taskIds = tasks.map { it.id }.toSet()
        val caseIds = cases.map { it.id }.toSet()
        fun dup(name: String, ids: List<String>) = ids.groupBy { it }.filter { it.value.size > 1 }.keys.forEach { p += "duplicate $name id $it" }
        dup("question", questions.map { it.id }); dup("lesson", lessons.map { it.id }); dup("flashcard", flashcards.map { it.id })
        questions.forEach { q ->
            p += Scoring.validate(q)
            if (q.taskId !in taskIds) p += "${q.id}: unknown task ${q.taskId}"
            else if (!q.taskId.startsWith(q.domain.name)) p += "${q.id}: task ${q.taskId} not in domain ${q.domain}"
            if (q.caseId != null && q.caseId !in caseIds) p += "${q.id}: unknown case ${q.caseId}"
        }
        lessons.forEach { if (it.taskId !in taskIds) p += "${it.id}: unknown task ${it.taskId}" }
        flashcards.forEach { if (it.taskId !in taskIds) p += "${it.id}: unknown task ${it.taskId}" }
        resources.forEach { if (!it.url.startsWith("https://")) p += "${it.id}: resource url must be https" }
        institutions.forEach {
            if (it.partnership == PartnershipStatus.VERIFIED_PARTNER) p += "${it.id}: VERIFIED_PARTNER needs signed authorization; not allowed in bundled seed"
        }
        return p
    }

    companion object {
        val json = Json { ignoreUnknownKeys = true; encodeDefaults = false }
        fun parse(text: String): ContentBundle = json.decodeFromString(serializer(), text)
    }
}
