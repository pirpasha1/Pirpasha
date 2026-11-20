package org.openpm.prep.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.openpm.engine.Domain
import org.openpm.prep.LocalContainer
import org.openpm.prep.data.Settings
import org.openpm.prep.ui.common.InfoCard
import org.openpm.prep.ui.common.Ring
import org.openpm.prep.ui.common.ScoreBar
import org.openpm.prep.ui.common.SectionTitle
import org.openpm.prep.ui.common.Sparkline
import org.openpm.prep.ui.common.formatHours
import java.time.LocalDate
import java.time.LocalTime
import java.time.temporal.ChronoUnit

@Composable
fun HomeScreen(settings: Settings, navigate: (String) -> Unit) {
    val c = LocalContainer.current
    val d by c.progress.dashboard.collectAsState(initial = null)
    val dash = d ?: return
    val greeting = when (LocalTime.now().hour) { in 5..11 -> "Good morning"; in 12..16 -> "Good afternoon"; else -> "Good evening" }
    val nextLesson = c.content.bundle.lessons.firstOrNull { it.id == settings.lastLessonId && it.id !in dash.completedLessons }
        ?: c.content.bundle.lessons.firstOrNull { it.id !in dash.completedLessons }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).widthIn(max = 840.dp)) {
        Text("$greeting${settings.displayName.takeIf { it.isNotBlank() }?.let { ", $it" } ?: ""}", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        settings.examEpochDay?.let {
            val days = ChronoUnit.DAYS.between(LocalDate.now(), LocalDate.ofEpochDay(it))
            Text(if (days >= 0) "$days days to your exam" else "Exam date passed – update it in Profile", color = MaterialTheme.colorScheme.onSurfaceVariant)
        } ?: Text("Free PMP® exam preparation · July 2026 exam format", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(16.dp))

        InfoCard {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Ring(dash.readiness)
                Spacer(Modifier.width(20.dp))
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Stat("Study time", formatHours(dash.studySeconds))
                    Stat("Lessons", "${dash.lessonsDone}/${dash.lessonsTotal}")
                    Stat("Last practice", dash.lastPractice?.scorePct?.let { "%.0f%%".format(it) } ?: "–")
                    Stat("Last mock", dash.lastMock?.scorePct?.let { "%.0f%%".format(it) } ?: "–")
                }
            }
            Text("Readiness is a study guide, not a pass prediction.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 8.dp))
        }

        if (dash.inProgress.isNotEmpty()) {
            SectionTitle("Resume")
            dash.inProgress.take(3).forEach { a ->
                InfoCard(Modifier.padding(bottom = 8.dp), onClick = { navigate("exam/${a.id}") }) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.PlayArrow, null)
                        Spacer(Modifier.width(8.dp))
                        Column(Modifier.weight(1f)) { Text(a.title, fontWeight = FontWeight.Medium); Text("${a.questionCount} questions · in progress", style = MaterialTheme.typography.bodySmall) }
                    }
                }
            }
        }

        SectionTitle("Continue learning")
        if (nextLesson != null) {
            InfoCard(onClick = { navigate("lesson/${nextLesson.id}") }) {
                Text(c.content.taskTitle(nextLesson.taskId).substringBefore(" · "), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.secondary)
                Text(nextLesson.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Text(nextLesson.summary, style = MaterialTheme.typography.bodyMedium, maxLines = 2)
                Row(verticalAlignment = Alignment.CenterVertically) { Text("${nextLesson.minutes} min read", style = MaterialTheme.typography.labelSmall); Spacer(Modifier.weight(1f)); Icon(Icons.AutoMirrored.Filled.ArrowForward, "Open") }
            }
        } else InfoCard { Text("All lessons completed. Focus on mocks and weak areas.") }

        SectionTitle("Today's plan")
        InfoCard {
            val goalMin = settings.dailyGoalMin
            Text("Studied ${dash.todaySeconds / 60} of $goalMin min today", fontWeight = FontWeight.Medium)
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { navigate("flashcards/ALL") }) { Text("${dash.cardsDue} cards due") }
                Button(onClick = { navigate("practice") }) { Text("Practice test") }
            }
        }

        if (dash.history.isNotEmpty()) {
            SectionTitle("Performance by domain")
            InfoCard {
                Domain.entries.forEach { dom ->
                    val t = dash.domainAccuracy.getValue(dom)
                    if (t.total > 0) ScoreBar("${dom.title} (${dom.weightPct}%)", t.pct, "${t.correct}/${t.total} correct · %.0f%%".format(t.pct), t.band)
                    else ScoreBar("${dom.title} (${dom.weightPct}%)", 0.0, "No attempts yet")
                }
                if (dash.mockTrend.size >= 2) {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 8.dp)) { Text("Mock trend  ", style = MaterialTheme.typography.labelMedium); Sparkline(dash.mockTrend, Modifier.weight(1f)) }
                }
                TextButton(onClick = { navigate("history") }) { Text("All results & analytics") }
            }
        }

        SectionTitle("Upcoming learning")
        InfoCard(onClick = { navigate("resources") }) {
            Text("Free webinars, PMI chapter events and open resources", fontWeight = FontWeight.Medium)
            Text("Each link shows its source, cost and the date it was verified.", style = MaterialTheme.typography.bodySmall)
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun Stat(label: String, value: String) = Row(Modifier.fillMaxWidth()) {
    Text(label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(1f))
    Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
}
