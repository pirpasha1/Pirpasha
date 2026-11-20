package org.openpm.prep.ui.exam

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.openpm.engine.Domain
import org.openpm.engine.ExamBlueprint
import org.openpm.engine.ExamEngine
import org.openpm.engine.ExamMode
import org.openpm.engine.Selector
import org.openpm.prep.AppContainer
import org.openpm.prep.LocalContainer
import org.openpm.prep.ui.common.InfoCard
import org.openpm.prep.ui.common.SectionTitle
import java.util.UUID

/** Builds and persists a new attempt; returns its id. */
suspend fun startAttempt(c: AppContainer, mode: ExamMode, bp: ExamBlueprint, domains: Set<Domain> = emptySet(), instant: Boolean = false): String {
    val id = UUID.randomUUID().toString()
    val selection = Selector(c.content.bundle.questions).build(bp, domains, c.progress.recentlySeen())
    val state = ExamEngine.start(id, mode, bp, selection, System.currentTimeMillis(), instant)
    c.progress.saveAttempt(state)
    return id
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun PracticeSetupScreen(onStart: (String) -> Unit) {
    val c = LocalContainer.current
    val scope = rememberCoroutineScope()
    var count by rememberSaveable { mutableIntStateOf(10) }
    var instant by rememberSaveable { mutableStateOf(true) }
    var domains by rememberSaveable { mutableStateOf(setOf<String>()) }
    val bank = c.content.bundle.questions.count { it.caseId == null && (domains.isEmpty() || it.domain.name in domains) }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).widthIn(max = 720.dp)) {
        Text("Practice", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text("Timed at the real exam pace (80 seconds per question).", color = MaterialTheme.colorScheme.onSurfaceVariant)
        SectionTitle("Number of questions")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { listOf(10, 30, 60).forEach { n -> FilterChip(count == n, { count = n }, label = { Text("$n questions") }) } }
        SectionTitle("Domains")
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(domains.isEmpty(), { domains = emptySet() }, label = { Text("All (weighted)") })
            Domain.entries.forEach { d -> FilterChip(d.name in domains, { domains = if (d.name in domains) domains - d.name else domains + d.name }, label = { Text(d.title) }) }
        }
        SectionTitle("Feedback")
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(if (instant) "Instant feedback" else "Results at the end", fontWeight = FontWeight.Medium)
                Text(if (instant) "Check each answer and read the explanation right away." else "Like the real exam: review everything after submitting.", style = MaterialTheme.typography.bodySmall)
            }
            Switch(instant, { instant = it })
        }
        Spacer(Modifier.height(12.dp))
        if (bank < count) Text("The current question bank has $bank eligible questions for this selection; the test will use all of them.",
            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.tertiary)
        Spacer(Modifier.height(12.dp))
        Button(onClick = {
            scope.launch { val id = startAttempt(c, ExamMode.PRACTICE, ExamBlueprint.practice(count), domains.map { Domain.valueOf(it) }.toSet(), instant); withContext(Dispatchers.Main) { onStart(id) } }
        }, modifier = Modifier.fillMaxWidth()) { Text("Start $count-question test") }
    }
}

@Composable
fun MockLobbyScreen(onStart: (String) -> Unit) {
    val c = LocalContainer.current
    val scope = rememberCoroutineScope()
    val dash by c.progress.dashboard.collectAsState(initial = null)
    val full = ExamBlueprint.PMP_2026_FULL
    val bankSize = c.content.bundle.questions.size
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).widthIn(max = 720.dp)) {
        Text("Mock exam", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text("Exam simulator for the PMP format launched in July 2026.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        dash?.inProgress?.filter { it.mode != ExamMode.PRACTICE }?.takeIf { it.isNotEmpty() }?.let { list ->
            SectionTitle("In progress")
            list.forEach { a -> InfoCard(Modifier.padding(vertical = 4.dp), onClick = { onStart(a.id) }) { Text("Resume: ${a.title}", fontWeight = FontWeight.Medium); Text("${a.questionCount} questions", style = MaterialTheme.typography.bodySmall) } }
        }
        SectionTitle("Choose an exam")
        InfoCard(Modifier.padding(vertical = 4.dp)) {
            Text(ExamBlueprint.DEMO.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text("20 questions · 25 minutes · results at the end. A quick way to try the exam interface.")
            TextButton(onClick = { scope.launch { val id = startAttempt(c, ExamMode.DEMO, ExamBlueprint.DEMO); withContext(Dispatchers.Main) { onStart(id) } } }) { Text("Start demo exam") }
        }
        InfoCard(Modifier.padding(vertical = 4.dp)) {
            Text(full.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text("${full.totalQuestions} questions · ${full.durationMin} minutes · 2 optional 10-minute breaks")
            full.sections.forEachIndexed { i, sec -> Text("${i + 1}. ${sec.name}: ${sec.questionCount} questions" + if (sec.breakAfter) " → break" else "", style = MaterialTheme.typography.bodySmall) }
            Text("Domain mix: People 33% · Process 41% · Business Environment 26% · about 40% predictive, 60% agile or hybrid.", style = MaterialTheme.typography.bodySmall)
            if (bankSize < full.totalQuestions) Text("The question bank currently holds $bankSize questions, so this mock uses all of them, with time scaled to the real pace. " +
                "It will grow to a full 180-question form as reviewed content is added.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.tertiary)
            TextButton(onClick = { scope.launch { val id = startAttempt(c, ExamMode.MOCK, full); withContext(Dispatchers.Main) { onStart(id) } } }) { Text("Start full mock") }
        }
        SectionTitle("Exam rules (simulated)")
        listOf(
            "Use Previous/Next or the palette to move within the current section.",
            "Flag questions to mark them for review.",
            "Ending a section locks it. A break may follow; the exam clock pauses during breaks.",
            "The exam submits automatically when time runs out.",
            "Multiple-response, matching and drag-and-drop items are all-or-nothing.",
        ).forEach { Text("• $it", style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(vertical = 2.dp)) }
        Spacer(Modifier.height(24.dp))
    }
}
