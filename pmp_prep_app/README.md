# OpenPM Prep: free PMP® exam preparation (Android)

OpenPM Prep is a free, independent study app for the PMP exam launched in July 2026. It covers all three domains (People 33%, Process 41%, Business Environment 26%) and has:
- lessons and flashcards;
- practice tests and a full mock-exam simulator;
- detailed explanations and analytics;
- a verified free-resource library.

> OpenPM Prep is not affiliated with, endorsed by, or sponsored by Project Management Institute (PMI). PMP, PMBOK and PMI are registered marks of Project Management Institute, Inc.

| Path | What |
|---|---|
| `docs/BLUEPRINT.md` | Architecture, database design, costs and timeline (Phase 1) |
| `docs/PHASE_REPORT_2-7.md` | What's built, test results and limitations |
| `docs/screenshots/` | Screens captured by the automated UI tests |
| `android/engine` | Pure-Kotlin exam engine (scoring, selection, timer state machine, results) |
| `android/app` | Jetpack Compose app |
| `content/` | Original study content (Python source) → `android/app/src/main/assets/content.json` |

## Build and test

You need JDK 17+ and the Android SDK (platform 35).

```bash
cd pmp_prep_app/content && python3 build_content.py   # after editing content
cd ../android
./gradlew :engine:test              # engine + content validation tests
./gradlew :app:testDebugUnitTest    # end-to-end UI flows (Robolectric); screenshots in app/build/screenshots
./gradlew :app:assembleDebug        # app/build/outputs/apk/debug/app-debug.apk
```

To install the debug APK on a phone, enable "Install unknown apps" and open the APK, or run `adb install app-debug.apk`.

Release signing reads `android/keystore.properties`, which must never be committed:
```
storeFile=/path/to/release.jks
storePassword=…
keyAlias=…
keyPassword=…
```

## Editing content
- Questions: `content/questions.py`. Use the helpers `S` (single choice), `M` (multiple response), `MATCH`, `ORDER`, `CAT`, and `CASES` for case studies.
- Lessons: `content/lessons.py`.
- Resources and institutions: `content/directory.py`. Add a resource only after checking its link and cost. Institutions stay `LISTED` unless there is a signed agreement.
- Run `build_content.py`, then `./gradlew :engine:test`. The `ContentTest` suite rejects invalid items.
