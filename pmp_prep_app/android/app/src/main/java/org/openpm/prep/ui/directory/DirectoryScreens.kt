package org.openpm.prep.ui.directory

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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.openpm.engine.PartnershipStatus
import org.openpm.engine.ResourceCategory
import org.openpm.prep.LocalContainer
import org.openpm.prep.data.EnquiryEntity
import org.openpm.prep.ui.common.BackBar
import org.openpm.prep.ui.common.InfoCard
import org.openpm.prep.ui.common.SmallTag
import org.openpm.prep.ui.common.rememberOpenUrl

@Composable
fun ResourcesScreen(navigate: (String) -> Unit) {
    val c = LocalContainer.current
    var tab by rememberSaveable { mutableIntStateOf(0) }
    var cat by rememberSaveable { mutableStateOf<String?>(null) }
    var query by rememberSaveable { mutableStateOf("") }
    val open = rememberOpenUrl()
    Column(Modifier.fillMaxSize()) {
        Text("Resources", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, modifier = Modifier.padding(16.dp, 16.dp, 16.dp, 8.dp))
        TabRow(tab) {
            Tab(tab == 0, { tab = 0 }, text = { Text("Free library") })
            Tab(tab == 1, { tab = 1 }, text = { Text("Institutions") })
        }
        if (tab == 0) {
            val list = c.content.bundle.resources.filter { cat == null || it.category.name == cat }
            LazyColumn(contentPadding = PaddingValues(16.dp)) {
                item {
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        item { FilterChip(cat == null, { cat = null }, label = { Text("All") }) }
                        items(ResourceCategory.entries.filter { e -> c.content.bundle.resources.any { it.category == e } }) { e ->
                            FilterChip(cat == e.name, { cat = e.name }, label = { Text(e.title) })
                        }
                    }
                    Text("Links open the owner's website. Nothing is re-hosted. Costs were checked on the date shown and may change.",
                        style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(vertical = 8.dp))
                }
                items(list, key = { it.id }) { r ->
                    InfoCard(Modifier.padding(vertical = 5.dp), onClick = { open(r.url) }) {
                        Text(r.title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                        Text(r.provider, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.secondary)
                        Text(r.description, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(vertical = 4.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { SmallTag(r.cost); SmallTag(r.licence.take(32)) }
                        Text("Verified ${r.lastVerified} · ${r.url.removePrefix("https://").substringBefore('/')}", style = MaterialTheme.typography.labelSmall, modifier = Modifier.padding(top = 4.dp))
                    }
                }
            }
        } else {
            val list = c.content.bundle.institutions.filter { query.isBlank() || it.name.contains(query, true) || it.country.contains(query, true) || it.type.contains(query, true) }
            LazyColumn(contentPadding = PaddingValues(16.dp)) {
                item {
                    OutlinedTextField(query, { query = it }, label = { Text("Search by name, type or country") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                    Text("Entries are public information. 'Listed' means no partnership exists. A 'Verified partner' badge appears only after written authorization.",
                        style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(vertical = 8.dp))
                }
                items(list, key = { it.id }) { i ->
                    InfoCard(Modifier.padding(vertical = 5.dp), onClick = { navigate("institution/${i.id}") }) {
                        Text(i.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                        Text("${i.type} · ${i.country}", style = MaterialTheme.typography.labelMedium)
                        Spacer(Modifier.height(4.dp))
                        PartnerBadge(i.partnership)
                    }
                }
                item {
                    Spacer(Modifier.height(12.dp))
                    OutlinedButton(onClick = { navigate("enquiry/new") }, modifier = Modifier.fillMaxWidth()) { Text("Partnership enquiry (for institutions)") }
                }
            }
        }
    }
}

@Composable
fun PartnerBadge(p: PartnershipStatus) = if (p == PartnershipStatus.VERIFIED_PARTNER)
    SmallTag(p.badge, MaterialTheme.colorScheme.secondaryContainer, MaterialTheme.colorScheme.onSecondaryContainer)
else SmallTag(p.badge, MaterialTheme.colorScheme.surfaceVariant, MaterialTheme.colorScheme.onSurfaceVariant)

@Composable
fun InstitutionScreen(id: String, navigate: (String) -> Unit, onBack: () -> Unit) {
    val c = LocalContainer.current
    val i = c.content.bundle.institutions.firstOrNull { it.id == id } ?: return
    val open = rememberOpenUrl()
    Scaffold(topBar = { BackBar(i.name, onBack) }) { pad ->
        Column(Modifier.padding(pad).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).widthIn(max = 720.dp)) {
            Text(i.name, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text("${i.type} · ${i.country}")
            Spacer(Modifier.height(6.dp)); PartnerBadge(i.partnership)
            Text(i.description, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(vertical = 12.dp))
            if (i.freeOfferings.isNotEmpty()) {
                Text("Free or public offerings", fontWeight = FontWeight.SemiBold)
                i.freeOfferings.forEach { Text("• $it") }
            }
            Spacer(Modifier.height(16.dp))
            Button(onClick = { open(i.website) }) { Text("Visit official website") }
            Text(i.website, style = MaterialTheme.typography.labelSmall, modifier = Modifier.padding(top = 4.dp))
            Spacer(Modifier.height(16.dp))
            OutlinedButton(onClick = { navigate("enquiry/${i.id}") }) { Text("Partnership enquiry") }
            Text("Listing here does not imply affiliation, accreditation or endorsement in either direction.",
                style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 12.dp))
        }
    }
}

@Composable
fun EnquiryScreen(id: String, onBack: () -> Unit) {
    val c = LocalContainer.current
    val inst = c.content.bundle.institutions.firstOrNull { it.id == id }
    var org by rememberSaveable { mutableStateOf(inst?.name ?: "") }
    var name by rememberSaveable { mutableStateOf("") }
    var email by rememberSaveable { mutableStateOf("") }
    var msg by rememberSaveable { mutableStateOf("") }
    var sent by rememberSaveable { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val emailOk = Regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$").matches(email.trim())
    Scaffold(topBar = { BackBar("Partnership enquiry", onBack) }) { pad ->
        Column(Modifier.padding(pad).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp).widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (sent) {
                Text("Thank you. Your enquiry has been saved.", style = MaterialTheme.typography.titleMedium)
                Text("It will be sent to the OpenPM Prep team when the app is connected to its backend. Until the backend is live, enquiries stay on this device.")
                Button(onClick = onBack) { Text("Done") }
                return@Column
            }
            Text("For training institutes, universities, PMI chapters and educators who want to offer free content or webinars to learners.")
            OutlinedTextField(org, { org = it }, label = { Text("Institution name") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(name, { name = it }, label = { Text("Contact person") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(email, { email = it }, label = { Text("Work email") }, isError = email.isNotBlank() && !emailOk,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email), modifier = Modifier.fillMaxWidth())
            OutlinedTextField(msg, { msg = it }, label = { Text("Proposal (free resources, webinars, sample courses…)") }, minLines = 4, modifier = Modifier.fillMaxWidth())
            Text("Submitting does not create a partnership. Verified partnerships require a written agreement.", style = MaterialTheme.typography.labelSmall)
            Button(enabled = org.isNotBlank() && name.isNotBlank() && emailOk && msg.length >= 20, onClick = {
                scope.launch {
                    c.progress.saveEnquiry(EnquiryEntity(institutionName = org.trim(), contactName = name.trim(), email = email.trim(), message = msg.trim(), createdAt = System.currentTimeMillis()))
                    sent = true
                }
            }) { Text("Submit enquiry") }
        }
    }
}
