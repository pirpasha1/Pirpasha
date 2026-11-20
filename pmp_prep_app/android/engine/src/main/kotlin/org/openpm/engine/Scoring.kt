package org.openpm.engine

/**
 * Scoring rules. PMI does not award partial credit, so every type is all-or-nothing.
 */
object Scoring {

    fun isAnswered(q: Question, r: Response?): Boolean {
        if (r == null) return false
        return when (q.type) {
            QuestionType.MCQ_SINGLE -> r.keys.size == 1
            QuestionType.MCQ_MULTI -> r.keys.isNotEmpty()
            QuestionType.DRAG_ORDER -> r.keys.size == q.items.size
            QuestionType.MATCHING -> r.pairs.keys.containsAll(q.left.map { it.key })
            QuestionType.DRAG_CATEGORIZE -> r.pairs.keys.containsAll(q.items.map { it.key })
        }
    }

    fun isCorrect(q: Question, r: Response?): Boolean {
        if (r == null || !isAnswered(q, r)) return false
        return when (q.type) {
            QuestionType.MCQ_SINGLE -> r.keys.single() == q.correct.single()
            QuestionType.MCQ_MULTI -> r.keys.toSet() == q.correct.toSet()
            QuestionType.DRAG_ORDER -> r.keys == q.correct
            QuestionType.MATCHING, QuestionType.DRAG_CATEGORIZE ->
                q.pairs.all { (k, v) -> r.pairs[k] == v }
        }
    }

    /** Count of correct sub-parts, shown in review only (never counted as score). */
    fun partialHits(q: Question, r: Response?): Pair<Int, Int> {
        if (r == null) return 0 to partsOf(q)
        return when (q.type) {
            QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTI ->
                r.keys.count { it in q.correct } to q.correct.size
            QuestionType.DRAG_ORDER ->
                r.keys.zip(q.correct).count { (a, b) -> a == b } to q.correct.size
            QuestionType.MATCHING, QuestionType.DRAG_CATEGORIZE ->
                q.pairs.count { (k, v) -> r.pairs[k] == v } to q.pairs.size
        }
    }

    private fun partsOf(q: Question) = when (q.type) {
        QuestionType.MATCHING, QuestionType.DRAG_CATEGORIZE -> q.pairs.size
        else -> q.correct.size
    }

    /** Validates authored content; returns a list of problems (empty = valid). Used by tests and the admin import. */
    fun validate(q: Question): List<String> {
        val p = mutableListOf<String>()
        if (q.stem.isBlank()) p += "${q.id}: empty stem"
        if (q.explanation.isBlank()) p += "${q.id}: missing explanation"
        when (q.type) {
            QuestionType.MCQ_SINGLE -> {
                if (q.options.size < 3) p += "${q.id}: needs >=3 options"
                if (q.correct.size != 1) p += "${q.id}: single choice needs exactly 1 correct key"
            }
            QuestionType.MCQ_MULTI -> {
                if (q.options.size < 4) p += "${q.id}: needs >=4 options"
                if (q.correct.size < 2) p += "${q.id}: multi response needs >=2 correct keys"
                if (q.selectCount != null && q.selectCount != q.correct.size) p += "${q.id}: selectCount != correct size"
            }
            QuestionType.DRAG_ORDER -> {
                if (q.correct.toSet() != q.items.map { it.key }.toSet()) p += "${q.id}: order must contain every item"
            }
            QuestionType.MATCHING -> {
                if (q.pairs.keys != q.left.map { it.key }.toSet()) p += "${q.id}: every left item needs a pair"
                if (!q.right.map { it.key }.containsAll(q.pairs.values)) p += "${q.id}: pair targets must exist"
            }
            QuestionType.DRAG_CATEGORIZE -> {
                if (q.pairs.keys != q.items.map { it.key }.toSet()) p += "${q.id}: every item needs a bucket"
                if (!q.buckets.map { it.key }.containsAll(q.pairs.values)) p += "${q.id}: bucket targets must exist"
            }
        }
        val keys = q.options.map { it.key }
        if (q.type == QuestionType.MCQ_SINGLE || q.type == QuestionType.MCQ_MULTI) {
            if (!keys.containsAll(q.correct)) p += "${q.id}: correct key not among options"
        }
        return p
    }
}
