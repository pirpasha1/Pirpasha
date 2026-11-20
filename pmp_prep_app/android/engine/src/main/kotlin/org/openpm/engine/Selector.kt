package org.openpm.engine

import kotlin.random.Random

data class Selection(
    val sections: List<List<String>>,
    /** Questions requested by the blueprint but not available in the bank. */
    val shortfall: Int,
)

/**
 * Builds an exam form from the bank: whole case studies for case sections,
 * then stratified sampling by domain weight and predictive/agile mix.
 */
class Selector(private val bank: List<Question>, private val random: Random = Random.Default) {

    fun build(
        blueprint: ExamBlueprint,
        domainFilter: Set<Domain> = emptySet(),
        avoidIds: Set<String> = emptySet(),
    ): Selection {
        val used = mutableSetOf<String>()
        var shortfall = 0
        val out = blueprint.sections.map { spec ->
            val picked = if (spec.caseStudy) pickCases(spec.questionCount, used) else mutableListOf()
            val remaining = spec.questionCount - picked.size
            // Case sections hold only case-study items; any gap is reported as shortfall.
            if (remaining > 0 && !spec.caseStudy) {
                val pool = bank.filter {
                    it.caseId == null && it.id !in used &&
                        (domainFilter.isEmpty() || it.domain in domainFilter)
                }
                picked += pickStratified(pool, remaining, blueprint, domainFilter, avoidIds)
            }
            used += picked
            shortfall += spec.questionCount - picked.size
            picked.toList()
        }
        return Selection(out, shortfall)
    }

    private fun pickCases(count: Int, used: Set<String>): MutableList<String> {
        val byCase = bank.filter { it.caseId != null && it.id !in used }.groupBy { it.caseId!! }
        val result = mutableListOf<String>()
        for ((_, qs) in byCase.entries.shuffled(random)) {
            if (result.size + qs.size > count) continue
            result += qs.map { it.id }
        }
        return result
    }

    private fun pickStratified(
        pool: List<Question>,
        count: Int,
        bp: ExamBlueprint,
        domainFilter: Set<Domain>,
        avoidIds: Set<String>,
    ): List<String> {
        val domains = if (domainFilter.isEmpty()) Domain.entries else Domain.entries.filter { it in domainFilter }
        val targets = apportion(count, domains.associateWith { bp.domainMix[it] ?: 0 })
        val chosen = mutableListOf<Question>()
        for (d in domains) {
            val inDomain = pool.filter { it.domain == d }
            chosen += pickWithApproachMix(inDomain, targets[d] ?: 0, bp.predictivePct, avoidIds)
        }
        // Top up from anything left if a domain was short.
        if (chosen.size < count) {
            val rest = pool.filter { it !in chosen }.sortedBy { if (it.id in avoidIds) 1 else 0 }
            chosen += preferFresh(rest, avoidIds).take(count - chosen.size)
        }
        return chosen.shuffled(random).map { it.id }
    }

    private fun pickWithApproachMix(qs: List<Question>, n: Int, predictivePct: Int, avoid: Set<String>): List<Question> {
        if (n <= 0) return emptyList()
        val pred = preferFresh(qs.filter { it.approach == Approach.PREDICTIVE }, avoid)
        val adaptive = preferFresh(qs.filter { it.approach != Approach.PREDICTIVE }, avoid)
        val wantPred = Math.round(n * predictivePct / 100.0).toInt()
        val p = pred.take(wantPred)
        val a = adaptive.take(n - p.size)
        val extra = (pred.drop(p.size)).take(n - p.size - a.size)
        return p + a + extra
    }

    /** Shuffle, but questions seen recently go last. */
    private fun preferFresh(qs: List<Question>, avoid: Set<String>): List<Question> {
        val (seen, fresh) = qs.shuffled(random).partition { it.id in avoid }
        return fresh + seen
    }

    companion object {
        /** Largest-remainder apportionment of [total] by integer weights. */
        fun <K> apportion(total: Int, weights: Map<K, Int>): Map<K, Int> {
            val sum = weights.values.sum()
            if (sum == 0 || total == 0) return weights.mapValues { 0 }
            val raw = weights.mapValues { total.toDouble() * it.value / sum }
            val base = raw.mapValues { it.value.toInt() }.toMutableMap()
            var left = total - base.values.sum()
            for (k in raw.entries.sortedByDescending { it.value - it.value.toInt() }.map { it.key }) {
                if (left == 0) break
                base[k] = base.getValue(k) + 1
                left--
            }
            return base
        }
    }
}
