package org.openpm.prep.ui.common

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import org.openpm.engine.Band
import org.openpm.engine.ContentLabel
import org.openpm.prep.ui.theme.okColor

const val DISCLAIMER = "OpenPM Prep is an independent, free study platform. It is not affiliated with, endorsed by, or sponsored by " +
    "Project Management Institute (PMI). PMP, PMBOK and PMI are registered marks of Project Management Institute, Inc."

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BackBar(title: String, onBack: () -> Unit, actions: @Composable () -> Unit = {}) {
    TopAppBar(
        title = { Text(title, maxLines = 1) },
        navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") } },
        actions = { actions() },
    )
}

@Composable
fun SectionTitle(text: String, modifier: Modifier = Modifier) =
    Text(text, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, modifier = modifier.padding(top = 16.dp, bottom = 8.dp))

@Composable
fun InfoCard(modifier: Modifier = Modifier, onClick: (() -> Unit)? = null, content: @Composable () -> Unit) {
    val colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    val m = modifier.fillMaxWidth()
    if (onClick != null) Card(onClick = onClick, modifier = m, colors = colors, elevation = CardDefaults.cardElevation(1.dp)) {
        Column(Modifier.padding(16.dp)) { content() }
    } else Card(modifier = m, colors = colors, elevation = CardDefaults.cardElevation(1.dp)) { Column(Modifier.padding(16.dp)) { content() } }
}

/** Readiness ring. */
@Composable
fun Ring(pct: Int, size: Dp = 112.dp, label: String = "Readiness") {
    val track = MaterialTheme.colorScheme.surfaceVariant
    val fill = MaterialTheme.colorScheme.secondary
    Box(Modifier.size(size).semantics { contentDescription = "$label $pct percent" }, contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(size)) {
            val stroke = Stroke(width = 12.dp.toPx(), cap = StrokeCap.Round)
            drawArc(track, -90f, 360f, false, style = stroke)
            drawArc(fill, -90f, 360f * pct.coerceIn(0, 100) / 100f, false, style = stroke)
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("$pct%", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(label, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
fun Sparkline(values: List<Double>, modifier: Modifier = Modifier) {
    val c = MaterialTheme.colorScheme.secondary
    Canvas(modifier.height(36.dp).widthIn(min = 80.dp)) {
        if (values.size < 2) return@Canvas
        val step = size.width / (values.size - 1)
        values.zipWithNext().forEachIndexed { i, (a, b) ->
            drawLine(c, Offset(i * step, size.height * (1 - a.toFloat() / 100)), Offset((i + 1) * step, size.height * (1 - b.toFloat() / 100)), 3.dp.toPx(), StrokeCap.Round)
        }
    }
}

@Composable
fun ScoreBar(label: String, pct: Double, detail: String, band: Band? = null) {
    Column(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            Text(band?.label ?: detail, style = MaterialTheme.typography.bodySmall, color = bandColor(band))
        }
        Spacer(Modifier.height(4.dp))
        LinearProgressIndicator(progress = { (pct / 100).toFloat() }, modifier = Modifier.fillMaxWidth().height(8.dp),
            color = bandColor(band).takeIf { band != null } ?: MaterialTheme.colorScheme.secondary, strokeCap = StrokeCap.Round)
        if (band != null) Text(detail, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
fun bandColor(b: Band?): Color = when (b) {
    Band.ABOVE_TARGET, Band.TARGET -> okColor()
    Band.BELOW_TARGET -> MaterialTheme.colorScheme.tertiary
    Band.NEEDS_IMPROVEMENT -> MaterialTheme.colorScheme.error
    null -> MaterialTheme.colorScheme.onSurfaceVariant
}

@Composable
fun LabelChip(label: ContentLabel, eco: String) {
    val demo = label == ContentLabel.DEMO
    AssistChip(
        onClick = {}, enabled = false,
        label = { Text(if (demo) "Demo content · $eco" else "Reviewed · $eco", style = MaterialTheme.typography.labelSmall) },
        shape = RoundedCornerShape(50),
        colors = AssistChipDefaults.assistChipColors(
            disabledContainerColor = if (demo) MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.secondaryContainer,
            disabledLabelColor = if (demo) MaterialTheme.colorScheme.onTertiaryContainer else MaterialTheme.colorScheme.onSecondaryContainer,
        ),
    )
}

@Composable
fun SmallTag(text: String, container: Color = MaterialTheme.colorScheme.primaryContainer, content: Color = MaterialTheme.colorScheme.onPrimaryContainer) {
    androidx.compose.material3.Surface(color = container, contentColor = content, shape = RoundedCornerShape(6.dp)) {
        Text(text, style = MaterialTheme.typography.labelSmall, modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp))
    }
}

@Composable
fun rememberOpenUrl(): (String) -> Unit {
    val ctx = LocalContext.current
    return { url -> runCatching { ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) } }
}

fun formatDuration(ms: Long): String {
    val s = (ms.coerceAtLeast(0) + 999) / 1000
    val h = s / 3600; val m = (s % 3600) / 60; val sec = s % 60
    return if (h > 0) "%d:%02d:%02d".format(h, m, sec) else "%02d:%02d".format(m, sec)
}

fun formatHours(seconds: Long): String = "%.1f h".format(seconds / 3600.0)
