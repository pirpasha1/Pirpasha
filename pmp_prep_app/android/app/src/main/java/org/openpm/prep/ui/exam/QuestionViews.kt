package org.openpm.prep.ui.exam

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.openpm.engine.CaseStudy
import org.openpm.engine.Choice
import org.openpm.engine.Question
import org.openpm.engine.QuestionType
import org.openpm.engine.Response
import org.openpm.engine.Scoring
import org.openpm.prep.ui.theme.okColor
import kotlin.random.Random

/** Stable per-attempt shuffle so options don't move when the screen recomposes or the app restarts. */
fun <T> List<T>.stableShuffle(seed: String): List<T> = shuffled(Random(seed.hashCode()))

@Composable
fun CaseHeader(case: CaseStudy) {
    var open by rememberSaveable(case.id) { mutableStateOf(true) }
    Surface(color = MaterialTheme.colorScheme.primaryContainer, shape = MaterialTheme.shapes.medium, modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Case study: ${case.title}", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                TextButton(onClick = { open = !open }) { Text(if (open) "Hide" else "Show") }
            }
            if (open) {
                Text(case.body, style = MaterialTheme.typography.bodyMedium)
                case.exhibits.forEach { ex ->
                    Surface(color = MaterialTheme.colorScheme.surface, shape = MaterialTheme.shapes.small, modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
                        Text("Exhibit: $ex", style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(10.dp))
                    }
                }
            }
        }
    }
}

/**
 * Renders the answer area for any item type. [reveal] shows correct/incorrect marking (instant feedback & review).
 * Every drag-and-drop type uses tap controls, so it also works with TalkBack and switch access.
 */
@Composable
fun AnswerArea(q: Question, seed: String, response: Response?, enabled: Boolean, reveal: Boolean, onChange: (Response) -> Unit) {
    when (q.type) {
        QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTI -> {
            val multi = q.type == QuestionType.MCQ_MULTI
            val opts = if (q.noShuffle) q.options else remember(seed) { q.options.stableShuffle(seed) }
            val selected = response?.keys ?: emptyList()
            if (multi) Text("Select ${q.selectCount ?: q.correct.size}.", style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(bottom = 6.dp))
            opts.forEachIndexed { i, o ->
                val isSel = o.key in selected
                val mark = if (!reveal) null else if (o.key in q.correct) true else if (isSel) false else null
                val rowMod = if (multi) Modifier.toggleable(isSel, enabled, Role.Checkbox) { checked ->
                    onChange(Response(if (checked) selected + o.key else selected - o.key))
                } else Modifier.selectable(isSel, enabled, Role.RadioButton) { onChange(Response(listOf(o.key))) }
                OptionRow(letter = ('A' + i).toString(), text = o.text, selected = isSel, mark = mark, modifier = rowMod) {
                    if (multi) Checkbox(isSel, null, enabled = enabled) else RadioButton(isSel, null, enabled = enabled)
                }
            }
        }
        QuestionType.MATCHING -> {
            val pairs = response?.pairs ?: emptyMap()
            val rights = remember(seed) { q.right.stableShuffle(seed) }
            q.left.forEach { l ->
                val chosen = pairs[l.key]
                val mark = if (!reveal) null else chosen == q.pairs[l.key]
                Column(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                    Text(l.text, fontWeight = FontWeight.Medium)
                    Picker(rights, chosen, enabled, mark) { onChange(Response(pairs = pairs + (l.key to it))) }
                    if (reveal && mark == false) Text("Correct: ${q.right.first { it.key == q.pairs[l.key] }.text}", style = MaterialTheme.typography.bodySmall, color = okColor())
                }
            }
        }
        QuestionType.DRAG_ORDER -> {
            val initial = remember(seed) { q.items.stableShuffle(seed).map { it.key } }
            val order = response?.keys?.takeIf { it.size == q.items.size } ?: initial
            val byKey = q.items.associateBy { it.key }
            Text("Use the arrows to put the items in order (first at the top).", style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(bottom = 6.dp))
            order.forEachIndexed { i, k ->
                val mark = if (!reveal) null else q.correct.getOrNull(i) == k
                OutlinedCard(Modifier.fillMaxWidth().padding(vertical = 3.dp), border = BorderStroke(1.dp, markColor(mark) ?: MaterialTheme.colorScheme.outline)) {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(start = 12.dp)) {
                        Text("${i + 1}.", fontWeight = FontWeight.Bold)
                        Spacer(Modifier.width(8.dp))
                        Text(byKey.getValue(k).text, Modifier.weight(1f).padding(vertical = 10.dp))
                        IconButton(enabled = enabled && i > 0, onClick = { onChange(Response(order.swap(i, i - 1))) }) { Icon(Icons.Filled.KeyboardArrowUp, "Move up") }
                        IconButton(enabled = enabled && i < order.lastIndex, onClick = { onChange(Response(order.swap(i, i + 1))) }) { Icon(Icons.Filled.KeyboardArrowDown, "Move down") }
                    }
                }
            }
            if (enabled && response?.keys?.size != q.items.size) OutlinedButton(onClick = { onChange(Response(order)) }, Modifier.padding(top = 6.dp)) { Text("Confirm this order") }
            if (reveal) Text("Correct order: " + q.correct.mapIndexed { i, k -> "${i + 1}. ${byKey.getValue(k).text}" }.joinToString("  "), style = MaterialTheme.typography.bodySmall, color = okColor(), modifier = Modifier.padding(top = 6.dp))
        }
        QuestionType.DRAG_CATEGORIZE -> {
            val pairs = response?.pairs ?: emptyMap()
            val items = remember(seed) { q.items.stableShuffle(seed) }
            Text("Tap a category for each item.", style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(bottom = 6.dp))
            items.forEach { item ->
                val mark = if (!reveal) null else pairs[item.key] == q.pairs[item.key]
                Column(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                    Text(item.text, fontWeight = FontWeight.Medium, color = markColor(mark) ?: Color.Unspecified)
                    BucketChips(q.buckets, pairs[item.key], enabled) { onChange(Response(pairs = pairs + (item.key to it))) }
                    if (reveal && mark != true) Text("Correct: ${q.buckets.first { it.key == q.pairs[item.key] }.text}", style = MaterialTheme.typography.bodySmall, color = okColor())
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun BucketChips(buckets: List<Choice>, selected: String?, enabled: Boolean, onPick: (String) -> Unit) {
    FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        buckets.forEach { b -> FilterChip(selected = selected == b.key, onClick = { onPick(b.key) }, enabled = enabled, label = { Text(b.text) }) }
    }
}

@Composable
private fun Picker(options: List<Choice>, selectedKey: String?, enabled: Boolean, mark: Boolean?, onPick: (String) -> Unit) {
    var open by remember { mutableStateOf(false) }
    Box {
        OutlinedButton(onClick = { open = true }, enabled = enabled, modifier = Modifier.fillMaxWidth(),
            border = BorderStroke(1.dp, markColor(mark) ?: MaterialTheme.colorScheme.outline)) {
            Text(options.firstOrNull { it.key == selectedKey }?.text ?: "Choose a match", Modifier.weight(1f))
            Icon(Icons.Filled.ArrowDropDown, null)
        }
        DropdownMenu(open, { open = false }) {
            options.forEach { o -> DropdownMenuItem(text = { Text(o.text) }, onClick = { onPick(o.key); open = false }) }
        }
    }
}

@Composable
private fun OptionRow(letter: String, text: String, selected: Boolean, mark: Boolean?, modifier: Modifier, control: @Composable () -> Unit) {
    val border = markColor(mark) ?: if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant
    OutlinedCard(modifier.fillMaxWidth().padding(vertical = 4.dp), border = BorderStroke(if (selected || mark != null) 2.dp else 1.dp, border)) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)) {
            control()
            Text("$letter.", fontWeight = FontWeight.Bold, modifier = Modifier.padding(end = 6.dp))
            Text(text, Modifier.weight(1f).padding(vertical = 8.dp))
            if (mark == true) Text("✓", color = okColor(), fontWeight = FontWeight.Bold)
            if (mark == false) Text("✗", color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun markColor(mark: Boolean?): Color? = when (mark) { true -> okColor(); false -> MaterialTheme.colorScheme.error; null -> null }

private fun List<String>.swap(a: Int, b: Int) = toMutableList().also { val t = it[a]; it[a] = it[b]; it[b] = t }

/** Explanation block with per-option rationales, used by instant feedback and review. */
@Composable
fun ExplanationBlock(q: Question, response: Response?, taskTitle: String) {
    val correct = Scoring.isCorrect(q, response)
    val (hit, of) = Scoring.partialHits(q, response)
    Surface(color = if (correct) okColor().copy(alpha = 0.12f) else MaterialTheme.colorScheme.errorContainer, shape = MaterialTheme.shapes.medium,
        modifier = Modifier.fillMaxWidth().padding(top = 12.dp)) {
        Column(Modifier.padding(14.dp)) {
            Text(if (correct) "Correct" else if (!Scoring.isAnswered(q, response)) "Not answered" else "Incorrect" +
                if (q.type != QuestionType.MCQ_SINGLE) " ($hit of $of parts right – no partial credit)" else "",
                fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(4.dp))
            Text(q.explanation, style = MaterialTheme.typography.bodyMedium)
            if (q.rationales.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                val opts = q.options.associateBy { it.key }
                q.options.forEachIndexed { i, o ->
                    q.rationales[o.key]?.let { why ->
                        val ok = o.key in q.correct
                        Text("${if (ok) "✓" else "✗"} ${opts[o.key]?.text?.take(60)}${if ((opts[o.key]?.text?.length ?: 0) > 60) "…" else ""}: $why",
                            style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(vertical = 2.dp))
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
            Text("Concept: ${q.concept.ifBlank { "–" }}", style = MaterialTheme.typography.labelMedium)
            Text(taskTitle, style = MaterialTheme.typography.labelSmall)
        }
    }
}
