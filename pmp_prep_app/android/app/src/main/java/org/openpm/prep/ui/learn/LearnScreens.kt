package org.openpm.prep.ui.learn

import android.os.SystemClock
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.outlined.Circle
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.openpm.engine.Domain
import org.openpm.prep.LocalContainer
import org.openpm.prep.ui.common.BackBar
import org.openpm.prep.ui.common.InfoCard
import org.openpm.prep.ui.common.LabelChip
import org.openpm.prep.ui.common.SectionTitle
import org.openpm.prep.ui.theme.okColor

@Composable
fun LearnScreen(navigate: (String) -> Unit) {
    val c = LocalContainer.current
    val dash by c.progress.dashboard.collectAsState(initial = null)
    val done = dash?.completedLessons ?: emptySet()
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).widthIn(max = 840.dp)) {
        Text("Learn", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, modifier = Modifier.semantics { heading() })
        Text("Organized by the PMP Exam Content Outline (${c.content.bundle.eco}).", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(8.dp))
        Domain.entries.forEach { d ->
            val lessons = c.content.lessonsOf(d)
            val n = lessons.count { it.id in done }
            InfoCard(Modifier.padding(vertical = 6.dp), onClick = { navigate("domain/${d.name}") }) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(d.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Text("${d.weightPct}% of exam · ${c.content.tasksOf(d).size} tasks", style = MaterialTheme.typography.bodySmall)
                    }
                    Text("$n/${lessons.size}", fontWeight = FontWeight.SemiBold)
                }
                Spacer(Modifier.height(8.dp))
                LinearProgressIndicator(progress = { if (lessons.isEmpty()) 0f else n.toFloat() / lessons.size }, Modifier.fillMaxWidth())
            }
        }
        SectionTitle("Study tools")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilledTonalButton(onClick = { navigate("flashcards/ALL") }, Modifier.weight(1f)) { Text("Flashcards") }
            FilledTonalButton(onClick = { navigate("revision") }, Modifier.weight(1f)) { Text("Quick revision") }
            FilledTonalButton(onClick = { navigate("faq") }, Modifier.weight(1f)) { Text("FAQ") }
        }
        Spacer(Modifier.height(16.dp))
        Text("Downloadable PDF packs are planned for v1.1. Official PDFs (Exam Content Outline, handbooks) are linked in Resources.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
fun DomainScreen(domainName: String, navigate: (String) -> Unit, onBack: () -> Unit) {
    val c = LocalContainer.current
    val d = Domain.valueOf(domainName)
    val dash by c.progress.dashboard.collectAsState(initial = null)
    val done = dash?.completedLessons ?: emptySet()
    Scaffold(topBar = { BackBar(d.title, onBack) }) { pad ->
        LazyColumn(Modifier.padding(pad).fillMaxSize(), contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)) {
            item {
                OutlinedButton(onClick = { navigate("flashcards/${d.name}") }) { Text("Flashcards for this domain") }
                Spacer(Modifier.height(8.dp))
            }
            items(c.content.tasksOf(d)) { t ->
                c.content.lessonsOf(t.id).forEach { l ->
                    InfoCard(Modifier.padding(vertical = 4.dp), onClick = { navigate("lesson/${l.id}") }) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            val complete = l.id in done
                            Icon(if (complete) Icons.Filled.CheckCircle else Icons.Outlined.Circle, if (complete) "Completed" else "Not completed",
                                tint = if (complete) okColor() else MaterialTheme.colorScheme.outline)
                            Spacer(Modifier.width(12.dp))
                            Column(Modifier.weight(1f)) {
                                Text("Task ${t.number}", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.secondary)
                                Text(t.title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                                Text("${l.minutes} min", style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun LessonScreen(lessonId: String, navigate: (String) -> Unit, onBack: () -> Unit) {
    val c = LocalContainer.current
    val lesson = c.content.lessonsById[lessonId] ?: return
    val scope = rememberCoroutineScope()
    val dash by c.progress.dashboard.collectAsState(initial = null)
    val complete = lessonId in (dash?.completedLessons ?: emptySet())
    // Track reading time while the lesson is open.
    DisposableEffect(lessonId) {
        val start = SystemClock.elapsedRealtime()
        scope.launch { c.settings.setLastLesson(lessonId) }
        onDispose {
            val secs = ((SystemClock.elapsedRealtime() - start) / 1000).coerceAtMost(3600)
            c.appScope.launch { c.progress.recordLessonTime(lessonId, secs) }
        }
    }
    val idx = c.content.bundle.lessons.indexOf(lesson)
    val next = c.content.bundle.lessons.getOrNull(idx + 1)
    Scaffold(topBar = { BackBar("Lesson", onBack) }) { pad ->
        Column(Modifier.padding(pad).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).widthIn(max = 720.dp)) {
            Text(c.content.taskTitle(lesson.taskId).substringBefore(" · ") + " · Task " + c.content.tasksById[lesson.taskId]!!.number,
                style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.secondary)
            Text(lesson.title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, modifier = Modifier.semantics { heading() })
            LabelChip(lesson.label, lesson.eco)
            Text(lesson.summary, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(vertical = 8.dp))
            lesson.body.forEach { p ->
                if (p.startsWith("- ")) Row(Modifier.padding(start = 8.dp, bottom = 4.dp)) { Text("•  "); Text(p.removePrefix("- "), style = MaterialTheme.typography.bodyLarge) }
                else Text(p, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(bottom = 10.dp))
            }
            SectionTitle("Key terms")
            lesson.keyTerms.forEach { t -> ExpandableTerm(t.term, t.definition) }
            if (lesson.example.isNotBlank()) Callout("Worked example", lesson.example, MaterialTheme.colorScheme.secondaryContainer)
            if (lesson.approachNote.isNotBlank()) Callout("Predictive vs agile", lesson.approachNote, MaterialTheme.colorScheme.primaryContainer)
            if (lesson.examTip.isNotBlank()) Callout("Exam mindset tip", lesson.examTip, MaterialTheme.colorScheme.tertiaryContainer)
            Spacer(Modifier.height(16.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { scope.launch { c.progress.setLessonComplete(lessonId, !complete) } }) { Text(if (complete) "Mark as not complete" else "Mark complete") }
                next?.let { OutlinedButton(onClick = { navigate("lesson/${it.id}") }) { Text("Next lesson") } }
            }
            Spacer(Modifier.height(32.dp))
        }
    }
}

@Composable
private fun Callout(title: String, text: String, color: androidx.compose.ui.graphics.Color) {
    Surface(color = color, shape = MaterialTheme.shapes.medium, modifier = Modifier.fillMaxWidth().padding(top = 12.dp)) {
        Column(Modifier.padding(14.dp)) {
            Text(title, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
            Text(text, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun ExpandableTerm(term: String, definition: String) {
    var open by rememberSaveable(term) { mutableStateOf(false) }
    Column(Modifier.fillMaxWidth().clickable(role = Role.Button) { open = !open }.animateContentSize().padding(vertical = 8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(term, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
            Icon(if (open) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore, if (open) "Collapse" else "Expand")
        }
        if (open) Text(definition, style = MaterialTheme.typography.bodyMedium)
    }
    HorizontalDivider()
}

@Composable
fun FlashcardScreen(domain: String, onBack: () -> Unit) {
    val c = LocalContainer.current
    val d = if (domain == "ALL") null else Domain.valueOf(domain)
    val reviews by c.progress.cardReviews().collectAsState(initial = null)
    val scope = rememberCoroutineScope()
    val r = reviews ?: return
    val byId = r.associateBy { it.cardId }
    val today = c.progress.today()
    // Due cards first (never-seen cards count as due), then the rest for extra practice.
    val deck = remember(domain) {
        c.content.cardsOf(d).sortedBy { card -> byId[card.id]?.dueEpochDay ?: Long.MIN_VALUE }
    }
    var index by rememberSaveable { mutableIntStateOf(0) }
    var flipped by rememberSaveable { mutableStateOf(false) }
    val due = deck.count { (byId[it.id]?.dueEpochDay ?: 0) <= today }
    Scaffold(topBar = { BackBar("Flashcards · ${d?.title ?: "All domains"}", onBack) }) { pad ->
        Column(Modifier.padding(pad).fillMaxSize().padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            if (deck.isEmpty()) { Text("No cards."); return@Column }
            val card = deck[index % deck.size]
            Text("Card ${index % deck.size + 1} of ${deck.size} · $due due", style = MaterialTheme.typography.labelLarge)
            Spacer(Modifier.height(12.dp))
            Card(
                onClick = { flipped = !flipped },
                modifier = Modifier.fillMaxWidth().widthIn(max = 600.dp).heightIn(min = 240.dp),
                colors = CardDefaults.cardColors(containerColor = if (flipped) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.primaryContainer),
            ) {
                Box(Modifier.fillMaxWidth().heightIn(min = 240.dp).padding(24.dp), contentAlignment = Alignment.Center) {
                    Text(if (flipped) card.back else card.front, style = if (flipped) MaterialTheme.typography.bodyLarge else MaterialTheme.typography.headlineSmall, textAlign = TextAlign.Center)
                }
            }
            Text(c.content.taskTitle(card.taskId), style = MaterialTheme.typography.labelSmall, modifier = Modifier.padding(8.dp), textAlign = TextAlign.Center)
            Text(if (flipped) "How well did you know it?" else "Tap the card to reveal the answer", style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(12.dp))
            if (flipped) Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("Again" to 1, "Hard" to 3, "Knew it" to 5).forEach { (label, q) ->
                    OutlinedButton(onClick = {
                        scope.launch { c.progress.reviewCard(card.id, byId[card.id], q) }
                        flipped = false; index++
                    }) { Text(label) }
                }
            }
        }
    }
}

@Composable
fun RevisionScreen(onBack: () -> Unit) {
    val c = LocalContainer.current
    var query by rememberSaveable { mutableStateOf("") }
    Scaffold(topBar = { BackBar("Quick revision", onBack) }) { pad ->
        LazyColumn(Modifier.padding(pad).fillMaxSize(), contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)) {
            item { Text("Formulas and must-know distinctions", style = MaterialTheme.typography.titleMedium); Spacer(Modifier.height(8.dp)) }
            items(c.content.bundle.revision) { t ->
                InfoCard(Modifier.padding(vertical = 4.dp)) { Text(t.term, fontWeight = FontWeight.SemiBold); Text(t.definition) }
            }
            item {
                SectionTitle("Glossary (from all lessons)")
                OutlinedTextField(query, { query = it }, label = { Text("Search terms") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
            }
            val terms = c.content.bundle.lessons.flatMap { it.keyTerms }.filter { query.isBlank() || it.term.contains(query, true) || it.definition.contains(query, true) }
            items(terms) { t -> Column(Modifier.padding(vertical = 6.dp)) { Text(t.term, fontWeight = FontWeight.SemiBold); Text(t.definition, style = MaterialTheme.typography.bodyMedium) }; HorizontalDivider() }
        }
    }
}

@Composable
fun FaqScreen(onBack: () -> Unit) {
    val c = LocalContainer.current
    Scaffold(topBar = { BackBar("Frequently asked questions", onBack) }) { pad ->
        LazyColumn(Modifier.padding(pad).fillMaxSize(), contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)) {
            items(c.content.bundle.faqs) { f -> ExpandableTerm(f.question, f.answer) }
        }
    }
}

