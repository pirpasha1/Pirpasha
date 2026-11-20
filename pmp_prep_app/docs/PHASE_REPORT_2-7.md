# Phase report: Phases 2–7 (Android app MVP)

**Date:** 20 November 2026 · **Build:** 0.1.0-mvp · **Content:** ECO-2026-07, content v1

## 1. Summary

| Phase | Scope | Status |
|---|---|---|
| 2 | Project scaffold, design system, navigation, guest access, Home dashboard | ✅ Done. Email/Google sign-in moved to Phase 8 (needs the backend). |
| 3 | Learn module: ECO structure, lessons, flashcards (SRS), quick revision, FAQ | ✅ Done. Downloadable PDF packs deferred to v1.1. |
| 4 | Question bank, engine (all item types), 10/30/60 practice tests | ✅ Done. The bank has 88 questions; the target is ≥ 300. |
| 5 | Mock simulator: sections, breaks, timer, palette, mark for review, auto-submit, resume | ✅ Done. The full 180-question form needs a larger bank (see §4). |
| 6 | Results, explanations, domain/approach/task analytics, readiness score | ✅ Done (on device). Cloud sync is in Phase 8. |
| 7 | Free resource library, institutions directory, partnership enquiry form | ✅ Done. Enquiries are stored on the device until the backend exists. |

## 2. What was built

**Android app** (`pmp_prep_app/android`), built with Kotlin 2.1, Jetpack Compose and Material 3. minSdk 26, targetSdk 35.

- `engine/` is a pure-Kotlin module with no Android dependencies, so it is fully unit-tested. It contains:
  - item models;
  - scoring for MCQ single, multiple response, matching, drag-order and drag-categorize, all all-or-nothing;
  - case studies (scenario plus exhibits plus sub-questions);
  - an exam blueprint stored as data, with the July 2026 format of 180 questions / 240 minutes / 2 breaks / case-study section first;
  - stratified selection by domain weight (33/41/26) and by approach (40% predictive), preferring questions not seen recently;
  - the exam state machine (sections, section lock, breaks that pause the exam clock, auto-submit on timeout, mark for review, instant feedback);
  - results (PMI-style bands, labelled as estimates), the readiness score, and SM-2 flashcard scheduling.
- `app/` contains:
  - 6-tab navigation: Home, Learn, Practice, Mock, Library (Resources), Profile. Phones get a bottom bar; tablets 600 dp and wider get a navigation rail.
  - Room database for attempts (full exam state, so an attempt survives process death), lesson progress, flashcard reviews, study time, enquiries and feedback.
  - DataStore settings: name, theme, text size, exam date, daily goal.
  - Light and dark themes, adjustable text size, TalkBack labels, and drag-and-drop items operated by taps (accessible alternative to dragging).
  - Onboarding with the independence disclaimer, plus privacy, terms and about screens (drafts that need legal review).
- `content/` holds the original study content as Python source, compiled to `app/src/main/assets/content.json`:
  - 26 lessons, one per task of the July 2026 ECO, each with key terms, a worked example, a predictive-vs-agile note and an exam tip;
  - 78 flashcards, 16 quick-revision formulas, 12 FAQs;
  - 88 practice questions, including 2 case studies, all labelled **DEMO** (not yet SME-reviewed);
  - 11 verified free resources and 7 institutions, all marked "Listed – not a partner".
- `.github/workflows/pmp-android.yml` is the CI workflow. It checks that the content bundle is current, runs all tests, builds the debug and release APKs and uploads them as artifacts.

## 3. Test results

| Suite | Tests | Result |
|---|---|---|
| `ScoringTest`: every item type, partial-hit reporting, content validation | 5 | ✅ pass |
| `SelectorTest`: domain apportionment (59/74/47 of 180), stratified practice, shortfall, domain filter, whole-case sections | 5 | ✅ pass |
| `ExamEngineTest`: 240-minute clock, auto-submit, break locks the section and pauses the clock, last-section rules, navigation and marking, serialization round-trip | 6 | ✅ pass |
| `ReadinessAndSm2Test` | 2 | ✅ pass |
| `ContentTest`: validates the **real** bundled content (26 tasks, every task has a lesson, all item types present, no unverified partners, a demo exam can be built) | 5 | ✅ pass |
| `AppFlowTest`: end-to-end on the real app under Robolectric (Room, DataStore, navigation, timer) | 4 flows | ✅ pass, 5 of 5 repeated runs |

The four end-to-end flows are:
1. Onboarding → Home → Learn → lesson → mark complete.
2. Practice test with instant feedback → mark for review → palette → submit → results → answer review.
3. Full mock → case study → end section → break → resume → save and exit → resume from lobby → submit → results.
4. Resources → institutions → partnership enquiry → profile dark mode.

Screenshots captured during these tests are in [`docs/screenshots/`](screenshots/).

The builds also passed: debug APK (18 MB) and release APK (1.8 MB, R8-minified, **unsigned**).

### Bugs found by testing and fixed
1. **Lost results (data loss).** After submitting, the exam screen's final save could overwrite the saved result, leaving the Results screen loading forever. Fixed: all writes now go through one mutex, and a submitted attempt is always saved together with its result.
2. **Case-study section padded with ordinary questions.** It now holds only case-study items.
3. **"30 minutes remaining" warning fired immediately** on short practice tests. Warnings now only fire for thresholds below the test's total time.
4. **Navigation called off the main thread** after a database save. It now always runs on the main thread.
5. **Bottom-tab labels were truncated** on phones. Phones now use short labels ("Mock", "Library").
6. **Content error in question R022.** The velocity forecast answer was 6 sprints; the correct answer is 7.

## 4. Limitations and what remains

- **Question bank size:** 88 original questions against a target of ≥ 300. Until it reaches 180, the "full mock" uses every available question and scales the time to the real pace (80 seconds per question). The app tells the learner this. The bank's predictive share is 56% (the target is 40%); the selector enforces the exam mix only when enough items exist.
- **All content is labelled DEMO.** It needs review by someone holding a PMP before it is labelled "Reviewed".
- **Timer behaviour:** the exam clock pauses while the app is closed. The real exam clock does not pause. This was chosen so that phone calls don't ruin a mock.
- **Drag-and-drop** uses tap controls (up/down arrows, category chips), not drag gestures. Gesture dragging can be added later; the tap mode stays as the accessible option.
- **Not tested on a physical device or emulator.** This cloud machine has no hardware virtualization (KVM), so UI tests ran under Robolectric. The minified release build compiles but has not been run. A device test is planned for Phase 9.
- **Not built yet:**
  - Email/Google accounts and cloud sync (Phase 8);
  - the admin dashboard and Supabase schema with RLS (Phase 8);
  - sending enquiries and feedback to the server (Phase 8);
  - the AI assistant, push notifications and PDF packs (v1.1).

## 5. Next step: Phase 8
Phase 8 covers:
- Supabase migrations: the tables from the blueprint, RLS policies, audit triggers and the draft → review → publish workflow.
- The React admin dashboard: content CRUD, mock builder, directory, enquiries, feedback, users and roles, exports.
- Email and Google auth with guest-to-account upgrade.
- Delta content sync and attempt sync in the app.

The following are needed from you **only when going live** (local development continues without them):
- a Supabase project URL and anon key;
- a Firebase project (for push notifications in v1.1);
- a Google Play Console account.
