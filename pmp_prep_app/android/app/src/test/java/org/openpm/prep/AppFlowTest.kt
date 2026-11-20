package org.openpm.prep

import android.graphics.Bitmap
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isDialog
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File

/**
 * End-to-end flows running the real app (Room, DataStore, navigation, exam engine) under Robolectric.
 * Screenshots are written to build/screenshots for the test report.
 */
@OptIn(ExperimentalTestApi::class)
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w411dp-h891dp-xxhdpi")
class AppFlowTest {
    @get:Rule val rule = createAndroidComposeRule<MainActivity>()

    private fun shot(name: String) {
        rule.waitForIdle()
        val view = rule.activity.window.decorView.rootView
        val bmp = Bitmap.createBitmap(view.width, view.height, Bitmap.Config.ARGB_8888)
        view.draw(android.graphics.Canvas(bmp))
        val dir = File("build/screenshots").apply { mkdirs() }
        File(dir, "$name.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    private fun waitText(text: String, substring: Boolean = false) = try {
        rule.waitUntilAtLeastOneExists(hasText(text, substring = substring), 10_000)
    } catch (e: Throwable) {
        shot("FAIL_" + text.filter { it.isLetterOrDigit() }); throw e
    }

    /** Settings (DataStore) persist across tests in one JVM, so onboarding is only shown to the first test. */
    private fun onboard() {
        rule.waitUntil(10_000) {
            rule.onAllNodesWithText("Continue as guest").fetchSemanticsNodes().isNotEmpty() ||
                rule.onAllNodesWithText("Continue learning").fetchSemanticsNodes().isNotEmpty()
        }
        if (rule.onAllNodesWithText("Continue as guest").fetchSemanticsNodes().isNotEmpty()) {
            shot("01_onboarding")
            rule.onNodeWithText("Your first name (optional)").performTextInput("Asha")
            rule.onNodeWithText("Continue as guest").performClick()
        }
        waitText("Continue learning")
    }

    @Test fun onboardingHomeAndLearn() {
        onboard()
        rule.onNodeWithText("Readiness is a study guide", substring = true).assertExists()
        shot("02_home")
        rule.onNodeWithText("Learn").performClick()
        waitText("People")
        shot("03_learn")
        rule.onNodeWithText("Process").performClick()
        waitText("Plan and manage schedule")
        rule.onNodeWithText("Plan and manage schedule").performScrollTo().performClick()
        waitText("Key terms")
        shot("04_lesson")
        rule.onNodeWithText("Mark complete").performScrollTo().performClick()
        waitText("Mark as not complete")
        rule.onNodeWithContentDescription("Back").performClick()
        rule.onNodeWithContentDescription("Back").performClick()
        waitText("1/10")
    }

    @Test fun practiceTestWithInstantFeedbackAndResults() {
        onboard()
        rule.onNodeWithText("Practice").performClick()
        waitText("Start 10-question test")
        shot("05_practice_setup")
        rule.onNodeWithText("Start 10-question test").performClick()
        waitText("Question 1 of 10")
        shot("06_question")
        // Answer whatever is on screen if it is a single/multiple choice item, then check it.
        val a = rule.onAllNodesWithText("A.")
        if (a.fetchSemanticsNodes().isNotEmpty()) {
            a.onFirst().performClick()
            rule.onNodeWithText("Check answer").performScrollTo().performClick()
            waitText("Concept:", substring = true)
            shot("07_instant_feedback")
        }
        rule.onNodeWithContentDescription("Mark for review").performClick()
        rule.onNodeWithContentDescription("Unmark for review").assertExists()
        rule.onNodeWithContentDescription("Question palette").performClick()
        waitText("question palette", substring = true)
        shot("08_palette")
        rule.onNode(hasText("2") and hasAnyAncestor(isDialog())).performClick()
        waitText("Question 2 of 10")
        rule.onNodeWithText("Submit").performClick()
        waitText("Submit exam?")
        rule.onNode(hasText("Submit") and hasAnyAncestor(isDialog())).performClick()
        waitText("Domain performance")
        rule.onNodeWithText("of 10 correct", substring = true).assertExists()
        shot("09_results")
        rule.onNodeWithText("All").performScrollTo().performClick()
        waitText("Answer review")
        rule.waitUntilAtLeastOneExists(hasText("Concept:", substring = true), 10_000)
        shot("10_review")
    }

    @Test fun fullMockSectionsBreaksAndResume() {
        onboard()
        rule.onNodeWithText("Mock").performClick()
        waitText("Start full mock")
        shot("11_mock_lobby")
        rule.onNodeWithText("Start full mock").performScrollTo().performClick()
        waitText("Question 1 of", substring = true)
        rule.onNodeWithText("Case study:", substring = true).assertExists()
        shot("12_case_study")
        // Jump to the last question of section 1 via the palette, then end the section.
        rule.onNodeWithContentDescription("Question palette").performClick()
        waitText("question palette", substring = true)
        rule.onNode(hasText("8") and hasAnyAncestor(isDialog())).performClick()
        waitText("End section")
        rule.onNodeWithText("End section").performClick()
        waitText("End this section?")
        rule.onNode(hasText("End section") and hasAnyAncestor(isDialog())).performClick()
        waitText("Break")
        rule.onNodeWithText("The exam clock is paused", substring = true).assertExists()
        shot("13_break")
        rule.onNodeWithText("Resume now").performClick()
        waitText("Independent questions – part A", substring = true)
        // Save & exit, then resume from the lobby.
        rule.onNodeWithText("Exit").performClick()
        rule.onNode(hasText("Save & exit") and hasAnyAncestor(isDialog())).performClick()
        waitText("In progress")
        rule.onNodeWithText("Resume: Full PMP mock (July 2026 format)").performClick()
        waitText("Independent questions – part A", substring = true)
        rule.onNodeWithText("Submit").performClick()
        rule.onNode(hasText("Submit") and hasAnyAncestor(isDialog())).performClick()
        waitText("Domain performance")
        shot("14_mock_results")
    }

    @Test fun resourcesInstitutionsAndProfile() {
        onboard()
        rule.onNodeWithText("Library").performClick()
        waitText("PMP Examination Content Outline (July 2026)")
        shot("15_resources")
        rule.onNodeWithText("Institutions").performClick()
        waitText("Project Management Institute (PMI)")
        rule.onAllNodesWithText("Listed – not a partner").onFirst().assertExists()
        shot("16_institutions")
        rule.onNodeWithText("Project Management Institute (PMI)").performClick()
        waitText("Visit official website")
        rule.onNodeWithText("Partnership enquiry").performClick()
        waitText("Submit enquiry")
        rule.onNodeWithText("Contact person").performTextInput("Test Person")
        rule.onNodeWithText("Work email").performTextInput("test@example.org")
        rule.onNodeWithText("Proposal (free resources, webinars, sample courses…)").performTextInput("We would like to offer a free monthly webinar for learners.")
        rule.onNodeWithText("Submit enquiry").performScrollTo().performClick()
        waitText("Thank you", substring = true)
        rule.onNodeWithText("Done").performClick()
        rule.onNodeWithContentDescription("Back").performClick()
        rule.onNodeWithText("Profile").performClick()
        waitText("Appearance")
        rule.onNodeWithText("Dark").performClick()
        rule.waitForIdle()
        shot("17_profile_dark")
        rule.onNodeWithText("Home").performClick()
        waitText("Continue learning")
        shot("18_home_dark")
    }
}
