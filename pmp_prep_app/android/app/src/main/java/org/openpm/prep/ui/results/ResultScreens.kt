package org.openpm.prep.ui.results

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.openpm.engine.Approach
import org.openpm.engine.Domain
import org.openpm.engine.ExamState
import org.openpm.engine.Scoring
import org.openpm.engine.Tally
import org.openpm.prep.LocalContainer
import org.openpm.prep.ui.common.BackBar
import org.openpm.prep.ui.common.DISCLAIMER
import org.openpm.prep.ui.common.InfoCard
import org.openpm.prep.ui.common.ScoreBar
import org.openpm.prep.ui.common.SectionTitle
import org.openpm.prep.ui.common.SmallTag
import org.openpm.prep.ui.common.Sparkline
import org.openpm.prep.ui.common.bandColor
import org.openpm.prep.ui.common.formatDuration
import org.openpm.prep.ui.exam.AnswerArea
import org.openpm.prep.ui.exam.CaseHeader
import org.openpm.prep.ui.exam.ExplanationBlock
import java.text.DateFormat
import java.util.Date

@Composable
fun ResultsScreen(attemptId: String, navigate: (String) -> Unit, onBack: () -> Unit) {
    val c = LocalContainer.current
    val a by c.progress.attempt(attemptId).collectAsState(initial = null)
    val r = a?.result
    Scaffold(topBar = { BackBar("Results", onBack) }) { pad ->
        if (r == null) { Column(Modifier.padding(pad).fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) { CircularProgressIndicator() }; return@Scaffold }
        Column(Modifier.padding(pad).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).widthIn(max = 760.dp)) {
            Text(a!!.title, style = MaterialTheme.typography.titleMedium)
            InfoCard(Modifier.padding(vertical = 8.dp)) {
                Text("%.0f%%".format(r.pct), style = MaterialTheme.typography.displaySmall, fontWeight = FontWeight.Bold, color = bandColor(r.band))
                Text("${r.correct} of ${r.total} correct · ${r.band.label} (estimate)", fontWeight = FontWeight.Medium)
                Text("Unanswered: ${r.unanswered} · Time used: ${formatDuration(r.timeUsedMs)}" + if (r.autoSubmitted) " · auto-submitted when time ran out" else "",
                    style = MaterialTheme.typography.bodySmall)
            }
            SectionTitle("Domain performance")
            InfoCard { Domain.entries.forEach { d -> r.byDomain[d]?.let { t -> ScoreBar(d.title, t.pct, "${t.correct}/${t.total} · %.0f%%".format(t.pct), t.band) } } }
            SectionTitle("By approach")
            InfoCard { Approach.entries.forEach { ap -> r.byApproach[ap]?.let { t -> ScoreBar(ap.name.lowercase().replaceFirstChar { it.uppercase() }, t.pct, "${t.correct}/${t.total}") } } }
            val weak = r.weakTasks()
            if (weak.isNotEmpty()) {
                SectionTitle("Weak areas to improve")
                InfoCard {
                    weak.forEach { (task, t) ->
                        val lesson = c.content.lessonsOf(task).firstOrNull()
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) { Text(c.content.taskTitle(task), style = MaterialTheme.typography.bodyMedium); Text("${t.correct}/${t.total} correct", style = MaterialTheme.typography.labelSmall) }
                            lesson?.let { TextButton(onClick = { navigate("lesson/${it.id}") }) { Text("Study") } }
                        }
                    }
                }
            }
            SectionTitle("Review answers")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { navigate("review/$attemptId/all") }) { Text("All") }
                OutlinedButton(onClick = { navigate("review/$attemptId/incorrect") }) { Text("Incorrect") }
                OutlinedButton(onClick = { navigate("review/$attemptId/marked") }) { Text("Marked") }
            }
            Spacer(Modifier.height(16.dp))
            Text("Performance bands use this app's thresholds (80/65/50%). PMI does not publish its passing score, so results are an estimate. $DISCLAIMER",
                style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(24.dp))
        }
    }
}

@Composable
fun ReviewScreen(attemptId: String, initialFilter: String, navigate: (String) -> Unit, onBack: () -> Unit) {
    val c = LocalContainer.current
    val state by produceState<ExamState?>(null, attemptId) { value = c.progress.loadState(attemptId) }
    var filter by rememberSaveable { mutableStateOf(initialFilter) }
    var report by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    Scaffold(topBar = { BackBar("Answer review", onBack) }) { pad ->
        val s = state ?: return@Scaffold
        val bank = c.content.questions
        val ids = s.allQuestionIds.filter { id ->
            val q = bank[id] ?: return@filter false
            when (filter) { "incorrect" -> !Scoring.isCorrect(q, s.responses[id]); "marked" -> id in s.marked; else -> true }
        }
        LazyColumn(Modifier.padding(pad).fillMaxSize(), contentPadding = PaddingValues(16.dp)) {
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("all" to "All", "incorrect" to "Incorrect", "marked" to "Marked").forEach { (k, l) -> FilterChip(filter == k, { filter = k }, label = { Text(l) }) }
                }
                if (ids.isEmpty()) Text("Nothing to show for this filter.", Modifier.padding(16.dp))
            }
            itemsIndexed(ids, key = { _, id -> id }) { _, id ->
                val q = bank.getValue(id)
                val n = s.allQuestionIds.indexOf(id) + 1
                InfoCard(Modifier.padding(vertical = 8.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text("Q$n", fontWeight = FontWeight.Bold)
                        SmallTag(q.domain.title); SmallTag(q.approach.name.lowercase())
                        if (id in s.marked) SmallTag("marked", MaterialTheme.colorScheme.tertiaryContainer, MaterialTheme.colorScheme.onTertiaryContainer)
                    }
                    Spacer(Modifier.height(6.dp))
                    q.caseId?.let { c.content.cases[it] }?.let { CaseHeader(it) }
                    Text(q.stem, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(bottom = 8.dp))
                    AnswerArea(q, "${s.attemptId}/$id", s.responses[id], enabled = false, reveal = true) {}
                    ExplanationBlock(q, s.responses[id], c.content.taskTitle(q.taskId))
                    Row {
                        c.content.lessonsOf(q.taskId).firstOrNull()?.let { l -> TextButton(onClick = { navigate("lesson/${l.id}") }) { Text("Open lesson") } }
                        TextButton(onClick = { report = id }) { Text("Report a problem") }
                    }
                }
            }
        }
    }
    report?.let { qid ->
        var text by remember { mutableStateOf("") }
        AlertDialog(onDismissRequest = { report = null }, title = { Text("Report a problem with $qid") },
            text = { OutlinedTextField(text, { text = it }, label = { Text("What's wrong?") }, minLines = 3) },
            confirmButton = { Button(enabled = text.isNotBlank(), onClick = { scope.launch { c.progress.saveFeedback(qid, "QUESTION_ERROR", text) }; report = null }) { Text("Save report") } },
            dismissButton = { TextButton(onClick = { report = null }) { Text("Cancel") } })
    }
}

@Composable
fun HistoryScreen(navigate: (String) -> Unit, onBack: () -> Unit) {
    val c = LocalContainer.current
    val dash by c.progress.dashboard.collectAsState(initial = null)
    Scaffold(topBar = { BackBar("Results & analytics", onBack) }) { pad ->
        val d = dash ?: return@Scaffold
        LazyColumn(Modifier.padding(pad).fillMaxSize(), contentPadding = PaddingValues(16.dp)) {
            item {
                SectionTitle("Overall by domain")
                InfoCard { Domain.entries.forEach { dom -> val t = d.domainAccuracy.getValue(dom); ScoreBar(dom.title, t.pct, "${t.correct}/${t.total}", t.band.takeIf { t.total > 0 }) } }
                if (d.mockTrend.size >= 2) { SectionTitle("Mock score trend"); InfoCard { Sparkline(d.mockTrend, Modifier.fillMaxWidth()) } }
                // Task heat list across all attempts.
                val byTask = d.history.mapNotNull { it.result }.flatMap { it.byTask.entries }.groupBy({ it.key }, { it.value })
                    .mapValues { (_, ts) -> Tally(ts.sumOf { it.correct }, ts.sumOf { it.total }) }
                if (byTask.isNotEmpty()) {
                    SectionTitle("Tasks (weakest first)")
                    InfoCard { byTask.entries.sortedBy { it.value.pct }.forEach { (task, t) -> ScoreBar(c.content.taskTitle(task), t.pct, "${t.correct}/${t.total} · %.0f%%".format(t.pct)) } }
                }
                SectionTitle("Attempts")
                if (d.history.isEmpty()) Text("No completed attempts yet.")
            }
            items(d.history) { a ->
                InfoCard(Modifier.padding(vertical = 4.dp), onClick = { navigate("results/${a.id}") }) {
                    Row {
                        Column(Modifier.weight(1f)) {
                            Text(a.title, fontWeight = FontWeight.Medium)
                            Text(DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(Date(a.startedAt)), style = MaterialTheme.typography.labelSmall)
                        }
                        Text("%.0f%%".format(a.scorePct ?: 0.0), fontWeight = FontWeight.Bold, color = bandColor(a.result?.band))
                    }
                }
            }
        }
    }
}

