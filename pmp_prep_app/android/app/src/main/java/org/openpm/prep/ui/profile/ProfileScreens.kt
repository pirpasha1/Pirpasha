package org.openpm.prep.ui.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.openpm.prep.BuildConfig
import org.openpm.prep.LocalContainer
import org.openpm.prep.data.Settings
import org.openpm.prep.data.ThemeMode
import org.openpm.prep.ui.common.BackBar
import org.openpm.prep.ui.common.DISCLAIMER
import org.openpm.prep.ui.common.InfoCard
import org.openpm.prep.ui.common.SectionTitle
import java.time.LocalDate

@Composable
fun OnboardingScreen() {
    val c = LocalContainer.current
    val scope = rememberCoroutineScope()
    var name by rememberSaveable { mutableStateOf("") }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp).widthIn(max = 560.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Spacer(Modifier.height(32.dp))
        Text("OpenPM Prep", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        Text("Free practice for the PMP® exam, for everyone.", style = MaterialTheme.typography.titleMedium)
        InfoCard {
            Text("• Lessons for all 26 tasks of the July 2026 Exam Content Outline")
            Text("• Practice tests, a full mock exam simulator and detailed explanations")
            Text("• Progress tracking and a free resource library")
            Text("• No fees, no subscriptions, no premium locks")
        }
        OutlinedTextField(name, { name = it }, label = { Text("Your first name (optional)") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        Button(onClick = { scope.launch { c.settings.completeOnboarding(name) } }, modifier = Modifier.fillMaxWidth()) { Text("Continue as guest") }
        OutlinedButton(onClick = {}, enabled = false, modifier = Modifier.fillMaxWidth()) { Text("Sign in with email or Google (coming with cloud sync)") }
        Text("Guest mode works fully offline; your progress stays on this device.", style = MaterialTheme.typography.bodySmall)
        Text(DISCLAIMER, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(settings: Settings, navigate: (String) -> Unit) {
    val c = LocalContainer.current
    val scope = rememberCoroutineScope()
    var name by rememberSaveable(settings.displayName) { mutableStateOf(settings.displayName) }
    var pickDate by remember { mutableStateOf(false) }
    var confirmReset by remember { mutableStateOf(false) }
    var scale by remember(settings.textScale) { mutableFloatStateOf(settings.textScale) }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).widthIn(max = 720.dp)) {
        Text("Profile", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text("Guest learner · data stored on this device", color = MaterialTheme.colorScheme.onSurfaceVariant)
        SectionTitle("You")
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(name, { name = it }, label = { Text("Display name") }, singleLine = true, modifier = Modifier.weight(1f))
            TextButton(onClick = { scope.launch { c.settings.setName(name) } }, enabled = name != settings.displayName) { Text("Save") }
        }
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 8.dp)) {
            Text("Exam date: " + (settings.examEpochDay?.let { LocalDate.ofEpochDay(it).toString() } ?: "not set"), Modifier.weight(1f))
            TextButton(onClick = { pickDate = true }) { Text("Set") }
            if (settings.examEpochDay != null) TextButton(onClick = { scope.launch { c.settings.setExamDay(null) } }) { Text("Clear") }
        }
        Text("Daily study goal", modifier = Modifier.padding(top = 8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { listOf(15, 30, 60, 90).forEach { m -> FilterChip(settings.dailyGoalMin == m, { scope.launch { c.settings.setGoal(m) } }, label = { Text("$m min") }) } }

        SectionTitle("Appearance")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            ThemeMode.entries.forEach { t -> FilterChip(settings.theme == t, { scope.launch { c.settings.setTheme(t) } }, label = { Text(t.name.lowercase().replaceFirstChar { it.uppercase() }) }) }
        }
        Text("Text size: ${(scale * 100).toInt()}%", modifier = Modifier.padding(top = 8.dp))
        Slider(scale, { scale = it }, valueRange = 0.85f..1.5f, steps = 12, onValueChangeFinished = { scope.launch { c.settings.setTextScale(scale) } })

        SectionTitle("Account & sync")
        Text("Email and Google sign-in, cloud sync across devices, the AI study assistant and notifications are being added. Your guest progress will carry over when you create an account.",
            style = MaterialTheme.typography.bodySmall)

        SectionTitle("Data & legal")
        LinkRow("Results & analytics") { navigate("history") }
        LinkRow("Privacy policy") { navigate("legal/privacy") }
        LinkRow("Terms of use") { navigate("legal/terms") }
        LinkRow("About & disclaimer") { navigate("legal/about") }
        Spacer(Modifier.height(8.dp))
        OutlinedButton(onClick = { confirmReset = true }) { Text("Delete all my data") }
        Spacer(Modifier.height(16.dp))
        Text("Version ${BuildConfig.VERSION_NAME} · content ${c.content.bundle.eco} v${c.content.bundle.contentVersion}", style = MaterialTheme.typography.labelSmall)
        Spacer(Modifier.height(24.dp))
    }
    if (pickDate) {
        val dp = rememberDatePickerState()
        DatePickerDialog(onDismissRequest = { pickDate = false },
            confirmButton = { TextButton(onClick = { dp.selectedDateMillis?.let { ms -> scope.launch { c.settings.setExamDay(ms / 86_400_000L) } }; pickDate = false }) { Text("OK") } },
            dismissButton = { TextButton(onClick = { pickDate = false }) { Text("Cancel") } }) { DatePicker(dp) }
    }
    if (confirmReset) {
        AlertDialog(onDismissRequest = { confirmReset = false }, title = { Text("Delete all data?") },
            text = { Text("This permanently removes your progress, results, flashcard history, saved enquiries and settings from this device.") },
            confirmButton = { Button(onClick = { confirmReset = false; scope.launch { c.progress.resetAll(); c.settings.clear() } }) { Text("Delete") } },
            dismissButton = { TextButton(onClick = { confirmReset = false }) { Text("Cancel") } })
    }
}

@Composable
private fun LinkRow(label: String, onClick: () -> Unit) {
    TextButton(onClick = onClick, modifier = Modifier.fillMaxWidth()) { Text(label, Modifier.weight(1f)) }
    HorizontalDivider()
}

@Composable
fun LegalScreen(doc: String, onBack: () -> Unit) {
    val (title, body) = when (doc) {
        "privacy" -> "Privacy policy" to PRIVACY
        "terms" -> "Terms of use" to TERMS
        else -> "About" to ABOUT
    }
    Scaffold(topBar = { BackBar(title, onBack) }) { pad ->
        Column(Modifier.padding(pad).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).widthIn(max = 720.dp)) {
            Text("Draft: to be reviewed by a qualified lawyer before public release.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.tertiary)
            body.split("\n\n").forEach { p -> Text(p, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(vertical = 6.dp)) }
        }
    }
}

private val ABOUT = """
OpenPM Prep is a free, independent learning platform that helps people prepare for the Project Management Professional (PMP)® certification exam regardless of their financial background.

$DISCLAIMER

All lessons and practice questions are original content written against the publicly available PMP Exam Content Outline (July 2026). They are not actual exam questions. Items marked "Demo content" have not yet been reviewed by a PMP-certified subject-matter expert.

Resource links point to their owners' websites and show the date each link was verified. Institution listings contain public information only and do not imply any partnership unless marked "Verified partner".
""".trim()

private val PRIVACY = """
What we collect in guest mode: nothing leaves your device. Your study progress, results, settings, enquiries and feedback are stored locally on your phone or tablet.

If you create an account (when cloud sync is available): your email address, display name, optional exam date and your learning progress, used only to sync your data and show your results. We do not sell personal data and show no advertising.

Analytics and crash reports: off by default; only enabled if you opt in.

Your rights: you can delete all local data at any time from Profile → Delete all my data. Account holders will be able to export and delete their account from within the app.

Children: the app is intended for adults preparing for a professional certification.

Contact: the project's support address will be published in the store listing.
""".trim()

private val TERMS = """
The app and its learning content are provided free of charge for personal educational use, as-is, without warranty. Passing the PMP exam is not guaranteed.

Do not share actual PMP exam questions in feedback or enquiries. Doing so breaches PMI's candidate agreement.

Third-party resources are subject to their owners' terms. Institution listings do not imply endorsement.

PMP, PMBOK and PMI are registered marks of Project Management Institute, Inc. This app is not affiliated with PMI.
""".trim()
