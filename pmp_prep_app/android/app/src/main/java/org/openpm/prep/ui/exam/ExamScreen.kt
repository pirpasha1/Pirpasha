package org.openpm.prep.ui.exam

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Apps
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.outlined.Flag
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.BottomAppBar
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import org.openpm.engine.ExamEngine
import org.openpm.engine.ExamState
import org.openpm.engine.Phase
import org.openpm.engine.Scoring
import org.openpm.prep.LocalContainer
import org.openpm.prep.ui.common.LabelChip
import org.openpm.prep.ui.common.SmallTag
import org.openpm.prep.ui.common.formatDuration
import org.openpm.prep.ui.theme.Amber

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ExamScreen(attemptId: String, onFinished: (String) -> Unit, onExit: () -> Unit) {
    val c = LocalContainer.current
    val vm: ExamViewModel = viewModel(key = attemptId, factory = viewModelFactory { initializer { ExamViewModel(c, attemptId) } })
    val st by vm.state.collectAsState()
    val s = st ?: return
    var showPalette by remember { mutableStateOf(false) }
    var confirmSubmit by remember { mutableStateOf(false) }
    var confirmExit by remember { mutableStateOf(false) }
    var confirmSection by remember { mutableStateOf(false) }
    val snack = remember { SnackbarHostState() }

    LaunchedEffect(s.phase) { if (s.phase == Phase.SUBMITTED) onFinished(attemptId) }
    // Time warnings at 30, 10 and 5 minutes.
    val warnBucket = when { s.timeRemainingMs <= 5 * 60_000 -> 5; s.timeRemainingMs <= 10 * 60_000 -> 10; s.timeRemainingMs <= 30 * 60_000 -> 30; else -> 0 }
    LaunchedEffect(warnBucket) { if (warnBucket > 0 && s.durationMs > warnBucket * 60_000L && s.phase == Phase.IN_SECTION) snack.showSnackbar("$warnBucket minutes or less remaining") }
    BackHandler { confirmExit = true }

    if (s.phase == Phase.ON_BREAK) { BreakScreen(s, vm::endBreak); return }
    if (s.phase == Phase.SUBMITTED) return

    val qid = s.currentQuestionId
    val q = vm.bank.getValue(qid)
    val sectionIds = s.section.questionIds
    val lastInSection = s.currentIndex == sectionIds.lastIndex
    val revealed = s.instantFeedback && qid in s.revealed

    Scaffold(
        snackbarHost = { SnackbarHost(snack) },
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Question ${s.overallNumber} of ${s.allQuestionIds.size}", style = MaterialTheme.typography.titleMedium)
                        Text(s.section.name + if (s.sections.size > 1) " · section ${s.currentSection + 1}/${s.sections.size}" else "", style = MaterialTheme.typography.labelSmall)
                    }
                },
                navigationIcon = { TextButton(onClick = { confirmExit = true }) { Text("Exit") } },
                actions = {
                    val low = s.timeRemainingMs < 5 * 60_000
                    Text(formatDuration(s.timeRemainingMs), fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold,
                        color = if (low) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.padding(end = 4.dp).semantics { contentDescription = "Time remaining ${formatDuration(s.timeRemainingMs)}" })
                    IconButton(onClick = { vm.toggleMark(qid) }) {
                        if (qid in s.marked) Icon(Icons.Filled.Flag, "Unmark for review", tint = Amber) else Icon(Icons.Outlined.Flag, "Mark for review")
                    }
                    IconButton(onClick = { showPalette = true }) { Icon(Icons.Filled.Apps, "Question palette") }
                },
            )
        },
        bottomBar = {
            BottomAppBar {
                OutlinedButton(onClick = vm::prev, enabled = s.currentIndex > 0) { Text("Previous") }
                Spacer(Modifier.weight(1f))
                TextButton(onClick = { confirmSubmit = true }) { Text("Submit") }
                Spacer(Modifier.weight(1f))
                when {
                    !lastInSection -> Button(onClick = vm::next) { Text("Next") }
                    !s.isLastSection -> Button(onClick = { confirmSection = true }) { Text("End section") }
                    else -> Button(onClick = { confirmSubmit = true }) { Text("Finish") }
                }
            }
        },
    ) { pad ->
        Column(Modifier.padding(pad).fillMaxSize()) {
            LinearProgressIndicator(progress = { s.overallNumber.toFloat() / s.allQuestionIds.size }, Modifier.fillMaxWidth())
            Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).widthIn(max = 760.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                    SmallTag(q.type.label)
                    if (s.instantFeedback) SmallTag(q.domain.title)
                    LabelChip(q.label, q.eco)
                }
                Spacer(Modifier.height(8.dp))
                q.caseId?.let { c.content.cases[it] }?.let { CaseHeader(it) }
                Text(q.stem, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(bottom = 12.dp))
                AnswerArea(q, "${s.attemptId}/$qid", s.responses[qid], enabled = !revealed, reveal = revealed) { vm.answer(qid, it) }
                if (s.instantFeedback) {
                    if (!revealed) Button(onClick = { vm.reveal(qid) }, enabled = Scoring.isAnswered(q, s.responses[qid]), modifier = Modifier.padding(top = 12.dp)) { Text("Check answer") }
                    else ExplanationBlock(q, s.responses[qid], c.content.taskTitle(q.taskId))
                }
                if (s.shortfall > 0 && s.overallNumber == 1) {
                    Text("Note: the question bank currently has fewer eligible questions than this format needs (${s.shortfall} short). Time was scaled to keep the real exam pace.",
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.tertiary, modifier = Modifier.padding(top = 16.dp))
                }
                Spacer(Modifier.height(24.dp))
            }
        }
    }

    if (showPalette) {
        ModalBottomSheet(onDismissRequest = { showPalette = false }) {
            Palette(s, vm.bank.mapValues { (id, q) -> Scoring.isAnswered(q, s.responses[id]) }) { i -> vm.goTo(i); showPalette = false }
        }
    }
    if (confirmSubmit) {
        val unanswered = s.allQuestionIds.count { !Scoring.isAnswered(vm.bank.getValue(it), s.responses[it]) }
        AlertDialog(onDismissRequest = { confirmSubmit = false },
            title = { Text("Submit exam?") },
            text = { Text("Unanswered: $unanswered\nMarked for review: ${s.marked.size}\n\nYou cannot change answers after submitting.") },
            confirmButton = { Button(onClick = { confirmSubmit = false; vm.submit() }) { Text("Submit") } },
            dismissButton = { TextButton(onClick = { confirmSubmit = false }) { Text("Keep working") } })
    }
    if (confirmSection) {
        AlertDialog(onDismissRequest = { confirmSection = false },
            title = { Text("End this section?") },
            text = { Text("Unanswered in this section: ${ExamEngine.unansweredInSection(s, vm.bank)}\nMarked: ${ExamEngine.markedInSection(s)}\n\n" +
                (if (s.section.breakAfter) "An optional 10-minute break follows. " else "") + "You cannot return to this section afterwards.") },
            confirmButton = { Button(onClick = { confirmSection = false; vm.finishSection() }) { Text("End section") } },
            dismissButton = { TextButton(onClick = { confirmSection = false }) { Text("Review section") } })
    }
    if (confirmExit) {
        AlertDialog(onDismissRequest = { confirmExit = false },
            title = { Text("Leave the exam?") },
            text = { Text("Your progress is saved. The timer pauses while you're away. Resume from Home or the Mock Exam tab.") },
            confirmButton = { Button(onClick = { confirmExit = false; vm.saveNow(); onExit() }) { Text("Save & exit") } },
            dismissButton = { TextButton(onClick = { confirmExit = false }) { Text("Stay") } })
    }
}

@Composable
private fun Palette(s: ExamState, answered: Map<String, Boolean>, onPick: (Int) -> Unit) {
    var filter by rememberSaveable { mutableStateOf("All") }
    Column(Modifier.padding(horizontal = 16.dp).padding(bottom = 24.dp)) {
        Text("${s.section.name} – question palette", style = MaterialTheme.typography.titleMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 8.dp)) {
            listOf("All", "Marked", "Unanswered").forEach { f -> FilterChip(filter == f, { filter = f }, label = { Text(f) }) }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.padding(bottom = 8.dp)) {
            Legend(MaterialTheme.colorScheme.primary, "Answered"); Legend(Amber, "Marked"); Legend(MaterialTheme.colorScheme.outline, "Unanswered")
        }
        val base = s.sections.take(s.currentSection).sumOf { it.questionIds.size }
        val entries = s.section.questionIds.withIndex().filter { (_, id) ->
            when (filter) { "Marked" -> id in s.marked; "Unanswered" -> answered[id] != true; else -> true }
        }
        LazyVerticalGrid(GridCells.Adaptive(52.dp), Modifier.height(320.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            itemsIndexed(entries) { _, (i, id) ->
                val isAns = answered[id] == true
                val marked = id in s.marked
                val current = i == s.currentIndex
                val color = when { marked -> Amber; isAns -> MaterialTheme.colorScheme.primary; else -> Color.Transparent }
                OutlinedCard(onClick = { onPick(i) }, modifier = Modifier.aspectRatio(1f),
                    border = BorderStroke(if (current) 3.dp else 1.dp, if (current) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.outline)) {
                    Surface(color = color, modifier = Modifier.fillMaxSize()) {
                        Box(contentAlignment = Alignment.Center) {
                            Text("${base + i + 1}", color = if (isAns || marked) Color.White else MaterialTheme.colorScheme.onSurface, fontWeight = FontWeight.Bold,
                                modifier = Modifier.semantics { contentDescription = "Question ${base + i + 1}, ${if (isAns) "answered" else "unanswered"}${if (marked) ", marked" else ""}" })
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun Legend(color: Color, label: String) = Row(verticalAlignment = Alignment.CenterVertically) {
    Surface(color = color, shape = MaterialTheme.shapes.extraSmall, modifier = Modifier.padding(end = 4.dp)) { Spacer(Modifier.height(12.dp).padding(6.dp)) }
    Text(label, style = MaterialTheme.typography.labelSmall)
}

@Composable
private fun BreakScreen(s: ExamState, onResume: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        Text("Break", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(formatDuration(s.breakRemainingMs), style = MaterialTheme.typography.displayMedium, fontFamily = FontFamily.Monospace,
            modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
        Spacer(Modifier.height(12.dp))
        Text("The exam clock is paused (${formatDuration(s.timeRemainingMs)} left). The previous section is now locked, as in the real exam. " +
            "The next section starts automatically when the break ends.", textAlign = TextAlign.Center)
        Spacer(Modifier.height(24.dp))
        Button(onClick = onResume) { Text("Resume now") }
    }
}
