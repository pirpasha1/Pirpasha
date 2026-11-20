package org.openpm.prep.ui

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.filled.EditNote
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.automirrored.filled.LibraryBooks
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Timer
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalConfiguration
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import org.openpm.prep.data.Settings
import org.openpm.prep.ui.directory.EnquiryScreen
import org.openpm.prep.ui.directory.InstitutionScreen
import org.openpm.prep.ui.directory.ResourcesScreen
import org.openpm.prep.ui.exam.ExamScreen
import org.openpm.prep.ui.exam.MockLobbyScreen
import org.openpm.prep.ui.exam.PracticeSetupScreen
import org.openpm.prep.ui.home.HomeScreen
import org.openpm.prep.ui.learn.DomainScreen
import org.openpm.prep.ui.learn.FaqScreen
import org.openpm.prep.ui.learn.FlashcardScreen
import org.openpm.prep.ui.learn.LearnScreen
import org.openpm.prep.ui.learn.LessonScreen
import org.openpm.prep.ui.learn.RevisionScreen
import org.openpm.prep.ui.profile.LegalScreen
import org.openpm.prep.ui.profile.OnboardingScreen
import org.openpm.prep.ui.profile.ProfileScreen
import org.openpm.prep.ui.results.HistoryScreen
import org.openpm.prep.ui.results.ResultsScreen
import org.openpm.prep.ui.results.ReviewScreen

enum class Tab(val route: String, val label: String, val icon: ImageVector, val short: String = label) {
    HOME("home", "Home", Icons.Filled.Home),
    LEARN("learn", "Learn", Icons.AutoMirrored.Filled.MenuBook),
    PRACTICE("practice", "Practice", Icons.Filled.EditNote),
    MOCK("mock", "Mock Exam", Icons.Filled.Timer, "Mock"),
    RESOURCES("resources", "Resources", Icons.AutoMirrored.Filled.LibraryBooks, "Library"),
    PROFILE("profile", "Profile", Icons.Filled.Person),
}

@Composable
fun AppRoot(settings: Settings) {
    if (!settings.onboarded) {
        OnboardingScreen()
        return
    }
    val nav = rememberNavController()
    val entry by nav.currentBackStackEntryAsState()
    val route = entry?.destination?.route
    val showNav = Tab.entries.any { it.route == route }
    val wide = LocalConfiguration.current.screenWidthDp >= 600

    Scaffold(
        bottomBar = { if (showNav && !wide) NavigationBar { Tab.entries.forEach { t -> NavigationBarItem(route == t.route, { nav.goTab(t) }, { Icon(t.icon, contentDescription = null) }, label = { Text(t.short, maxLines = 1, softWrap = false, style = MaterialTheme.typography.labelSmall) }) } } },
    ) { pad ->
        Row(Modifier.fillMaxSize().padding(pad)) {
            if (showNav && wide) NavigationRail { Tab.entries.forEach { t -> NavigationRailItem(route == t.route, { nav.goTab(t) }, { Icon(t.icon, null) }, label = { Text(t.label) }) } }
            AppNavHost(nav, settings)
        }
    }
}

private fun NavHostController.goTab(t: Tab) = navigate(t.route) {
    popUpTo(graph.findStartDestination().id) { saveState = true }
    launchSingleTop = true
    restoreState = true
}

@Composable
private fun AppNavHost(nav: NavHostController, settings: Settings) {
    val back: () -> Unit = { nav.popBackStack() }
    NavHost(nav, startDestination = Tab.HOME.route, modifier = Modifier.fillMaxSize()) {
        composable("home") { HomeScreen(settings, nav::navigate) }
        composable("learn") { LearnScreen(nav::navigate) }
        composable("practice") { PracticeSetupScreen { id -> nav.navigate("exam/$id") } }
        composable("mock") { MockLobbyScreen { id -> nav.navigate("exam/$id") } }
        composable("resources") { ResourcesScreen(nav::navigate) }
        composable("profile") { ProfileScreen(settings, nav::navigate) }

        composable("domain/{d}") { DomainScreen(it.arguments!!.getString("d")!!, nav::navigate, back) }
        composable("lesson/{id}") { LessonScreen(it.arguments!!.getString("id")!!, nav::navigate, back) }
        composable("flashcards/{d}") { FlashcardScreen(it.arguments!!.getString("d")!!, back) }
        composable("revision") { RevisionScreen(back) }
        composable("faq") { FaqScreen(back) }

        composable("exam/{id}") {
            ExamScreen(it.arguments!!.getString("id")!!, onFinished = { id ->
                nav.navigate("results/$id") { popUpTo("exam/$id") { inclusive = true } }
            }, onExit = back)
        }
        composable("results/{id}") { ResultsScreen(it.arguments!!.getString("id")!!, nav::navigate, back) }
        composable("review/{id}/{filter}") { ReviewScreen(it.arguments!!.getString("id")!!, it.arguments!!.getString("filter")!!, nav::navigate, back) }
        composable("history") { HistoryScreen(nav::navigate, back) }

        composable("institution/{id}") { InstitutionScreen(it.arguments!!.getString("id")!!, nav::navigate, back) }
        composable("enquiry/{id}") { EnquiryScreen(it.arguments!!.getString("id")!!, back) }
        composable("legal/{doc}") { LegalScreen(it.arguments!!.getString("doc")!!, back) }
    }
}
