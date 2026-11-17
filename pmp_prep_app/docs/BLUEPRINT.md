# Free PMP Exam Prep App: Development Blueprint and MVP Plan

**Status:** Phase 1 (requirements analysis and architecture). Waiting for owner approval before Phase 2 starts.
**Date:** 17 November 2026
**Working name:** *OpenPM Prep*. This is a placeholder; see §13.2 on trademarks.

---

## 1. Exam baseline the app is built against

The app targets the exam that is live now. PMI launched the updated PMP exam in July 2026. The figures below come from PMI's *PMP Examination Content Outline, July 2026 PMP Certification Exam Update* (pmi.org).

| Item | July 2026 exam (current) | 2021 exam (retired) |
|---|---|---|
| Domains | People **33%**, Process **41%**, Business Environment **26%** | People 42%, Process 50%, Business Environment 8% |
| Questions | 180 (170 scored + 10 unscored pretest) | 180 (175 + 5) |
| Time | **240 minutes** | 230 minutes |
| Breaks | Two 10-minute breaks: one after the case-study section, one about halfway through the independent questions. You cannot return to a section once you take its break. | Two 10-minute breaks |
| Approach mix | About 40% predictive; about 60% agile and hybrid | About 50 / 50 |
| Item types | Multiple choice (single or multiple response), drag-and-drop, and "practicum" hands-on items (tools, data, case study) | MCQ, multi-response, matching, hotspot, limited fill-in |
| New themes | AI, sustainability, value and outcomes, stakeholder engagement | — |

**Design rule:** exam formats are stored as **data** (an `exam_blueprints` table), not hard-coded. When PMI changes the exam again, an admin adds a new blueprint (domain weights, question count, time, break points, sections) without an app release. Every question, note and resource carries an `eco_version` tag (`ECO-2026-07` by default). The UI shows that tag so learners always know which outline a piece of content follows.

---

## 2. Requirements analysis

### 2.1 Users and roles
| Role | Where | Can do |
|---|---|---|
| Guest | App | Everything offline: study, practise, take mocks. Progress stays on the device only. |
| Learner | App | Everything a guest can, plus cloud sync, cross-device progress, AI assistant (with a daily limit) and notifications |
| Reviewer (SME) | Admin web | Review and approve draft questions and notes. Cannot publish alone. |
| Content Admin | Admin web | Create and edit content, build mock exams, publish approved content |
| Directory Admin | Admin web | Manage institutions, resources, webinars and the partnership enquiry inbox |
| Super Admin | Admin web | Everything above, plus roles, users, exports and settings |

### 2.2 Functional requirements mapped to modules
| Brief section | Module | MVP? |
|---|---|---|
| A. Dashboard | `feature-home` | Yes |
| B. Study materials (notes, definitions, examples, flashcards, PDFs, quick revision, FAQ) | `feature-learn` | Yes (PDF export is v1.1) |
| C. Exam simulator (10/30/60/180, timer, palette, mark for review, auto-submit) | `feature-practice`, `feature-exam` | Yes |
| C. Item types: MCQ, multi-response, scenario, matching, drag-and-drop, situational | `core-question-engine` | Yes, all six |
| D. Answer explanations and domain analytics | `feature-results` | Yes |
| E. Free resource library | `feature-resources` | Yes (verified links only) |
| F. Institution directory and partnership enquiry form | `feature-institutions` | Yes (directory listings only; no partnership claims) |
| G. AI learning assistant | `feature-assistant` + server function | v1.1 (built behind a feature flag) |
| 5. Admin dashboard with role-based access | `admin-web` | Yes |
| Auth: email, Google, guest | `core-auth` | Yes |
| Push notifications | FCM | v1.1 |
| Web version for learners | Reuse the admin-web stack | Future |

### 2.3 Non-functional requirements
- **Free forever.** No paywall code paths, no in-app billing library, no ads SDK in the MVP.
- **Offline-first.** Learners in low-bandwidth regions can do every core activity offline after install.
- **Low cost.** The backend runs on free tiers up to roughly 50,000 monthly active users.
- **Devices.** Android 8.0+ (API 26). Phones and tablets get adaptive layouts.
- **Accessibility.** WCAG 2.1 AA targets, TalkBack labels, dynamic font scaling, 48 dp touch targets, and drag-and-drop items that also work without dragging.
- **Privacy.** Minimal personal data, analytics opt-in, account deletion inside the app (Google Play requires this).
- **Integrity.** Learners can never write to content tables. All content changes are audited.

---

## 3. Technology choices

| Layer | Choice | Why |
|---|---|---|
| Android UI | **Kotlin 2.x + Jetpack Compose + Material 3**, adaptive layouts (WindowSizeClass) | Requested stack; modern; tablet-ready |
| Architecture | MVVM + clean layers, **Hilt** DI, Kotlin Coroutines/Flow, **Navigation-Compose** | Standard, testable |
| Local DB | **Room** (SQLite), with the question bank seeded from bundled JSON | Offline-first; guest mode needs no server |
| Preferences | DataStore | Theme, onboarding, exam settings |
| Backend | **Supabase**: PostgreSQL, Auth (email + Google), Storage, Edge Functions, Row-Level Security | One free-tier service covers DB, auth, files and server functions. Postgres plus RLS gives row-level access control for the admin roles. No vendor lock-in, since it is plain Postgres. |
| Sync | Supabase Kotlin client (supabase-kt) plus a WorkManager sync job | Background, retry-safe |
| Push | **Firebase Cloud Messaging only** | Free; the standard on Android |
| Admin dashboard | **React + TypeScript + Vite**, using the Supabase JS client, hosted on Cloudflare Pages or Netlify (free) | Fast to build; the same codebase can become the learner web app later |
| AI assistant | Supabase Edge Function proxy, with a pluggable provider: an open-weight model through a low-cost host, or a Claude Haiku-class model | API keys stay on the server; per-user daily quotas |
| Analytics | Self-computed learning analytics in Postgres, plus optional, consent-gated Firebase Analytics or self-hosted PostHog | Privacy-conscious |
| Crash reporting | Firebase Crashlytics (opt-in) | Free |
| CI/CD | GitHub Actions: lint, unit tests, debug APK, signed release AAB | Reproducible builds |

**Alternative considered: all-Firebase (Firestore).** It works, but Firestore's per-read pricing scales badly for question banks and analytics queries, and its role-based rules for multi-role admins are harder to audit than Postgres RLS. I recommend Supabase. Switching is possible because the repository layer hides the backend.

---

## 4. System architecture

```
┌────────────────────────── Android app (Kotlin/Compose) ──────────────────────────┐
│  UI (Compose screens)  →  ViewModels  →  Use-cases  →  Repositories               │
│                                                    ├─ Room DB (offline source of truth)
│                                                    └─ Remote data source (supabase-kt)
│  Question engine (pure Kotlin, unit-tested): renderers + scorers per item type    │
│  Exam session engine: timer, sections, breaks, autosave, auto-submit              │
│  WorkManager: content pull + attempt/progress push                                │
└──────────────────────────────────────┬───────────────────────────────────────────┘
                                       │ HTTPS (anon key + user JWT; RLS enforces access)
┌──────────────────────────────────────▼───────────────────────────────────────────┐
│ Supabase                                                                         │
│  Auth (email, Google, anonymous→upgrade)   Postgres + RLS   Storage (PDFs, images)│
│  Edge Functions: ai-assistant (quota + provider key), publish-content,            │
│                  export-reports, delete-account                                   │
│  pg_cron: nightly analytics rollups, link checker                                 │
└──────────────┬───────────────────────────────────────────┬───────────────────────┘
               │                                           │
   ┌───────────▼───────────┐                   ┌───────────▼───────────┐
   │ Admin web (React)      │                   │ FCM (push)            │
   │ role-based UI + RLS    │                   │ AI provider (server)  │
   └───────────────────────┘                   └───────────────────────┘
```

**Content flow:** an author writes a draft (status `draft`). A reviewer approves it (`approved`). A content admin publishes it (`published`, content version incremented). Apps fetch the change set since their last `content_version`. Questions ship inside the APK as well, so first launch works offline.

### 4.1 Android module layout
```
pmp_prep_app/android/
  app/                      – entry point, navigation graph, theming
  core/model                – domain models (Question, ExamBlueprint, Attempt…)
  core/database             – Room entities, DAOs, seed loader
  core/network              – Supabase client wrapper
  core/data                 – repositories + sync
  core/question-engine      – item types, scoring, shuffling (pure Kotlin)
  core/designsystem         – colours, typography, components
  feature/home  feature/learn  feature/practice  feature/exam
  feature/results  feature/resources  feature/institutions
  feature/assistant  feature/profile  feature/auth
pmp_prep_app/admin-web/     – React admin dashboard
pmp_prep_app/supabase/      – migrations (SQL), RLS policies, edge functions, seed
pmp_prep_app/content/       – original question bank + notes as JSON/Markdown (source-controlled)
pmp_prep_app/docs/          – blueprint, DB schema, guides, test reports
```

---

## 5. Proposed screens

Bottom navigation (6 tabs, as requested): **Home · Learn · Practice · Mock Exam · Resources · Profile**. On phones, Practice and Mock Exam share an icon group. On tablets they are full items in a navigation rail.

| # | Screen | Key contents |
|---|---|---|
| 1 | Splash / onboarding | Mission statement, independence disclaimer, choose "Continue as guest" / "Sign in" |
| 2 | Sign-in / register | Email + password, Google, guest; upgrade guest account later without losing progress |
| 3 | **Home dashboard** | Greeting, readiness % ring, study hours, chapters completed, last practice score, mock trend sparkline, "Continue learning" card, today's plan, upcoming webinars |
| 4 | Learn – domain list | People / Process / Business Environment with weight %, progress bars, ECO version tag |
| 5 | Learn – task list | ECO tasks per domain with completion ticks |
| 6 | Lesson reader | Notes, key definitions (expandable), worked example, "predictive vs agile" callouts, mark complete, font size control |
| 7 | Flashcards | Swipe deck, flip, "know / again" spaced-repetition (SM-2) |
| 8 | Quick revision & FAQ | One-page summaries, searchable FAQ |
| 9 | Practice setup | Choose 10/30/60 questions, domain/task filter, approach filter (predictive/agile/hybrid), mode: *instant feedback* or *end-of-test* |
| 10 | **Question player** | Timer, progress, question body by type, Mark-for-review flag, Prev/Next, palette button |
| 11 | Question palette (sheet) | Grid coloured: answered / unanswered / marked / current; filter "marked only" |
| 12 | Mock exam lobby | Choose: Short demo (≈20 q / 25 min), Full mock (blueprint-driven, 180 q / 240 min with sections + 2 breaks), Custom; exam rules |
| 13 | Break screen | 10-min countdown, "section is now locked" warning, resume early |
| 14 | Submit confirm | Counts of unanswered / marked; auto-submit on time-out |
| 15 | **Results summary** | Score %, performance band per domain (Above Target / Target / Below / Needs Improvement, mirroring PMI's reporting style), time used, pass-likelihood indicator (clearly labelled as an estimate) |
| 16 | Answer review | Filter all / incorrect / marked; each item: your answer, correct answer, explanation, why each distractor is wrong, linked concept & lesson |
| 17 | Analytics | Domain & task heat-map, approach breakdown, history chart, weak areas → "Practise these" |
| 18 | Resources library | Category tabs (PMI official, guides, videos, webinars, articles, sample questions, OER); each card shows source, licence, "verified on" date; opens externally |
| 19 | Institutions directory | Search/filter by country & type; profile page; "Listed — not a partner" vs "Verified partner" badge |
| 20 | Partnership enquiry form | Institution name, contact, proposal; stored server-side for admins |
| 21 | AI assistant (v1.1) | Chat, "Explain this question" entry from review, daily quota meter, "AI can be wrong" notice |
| 22 | Profile & settings | Account, exam date + study plan, theme (system/light/dark), text size, notifications, data export, delete account, privacy policy, terms, about/disclaimer |

### 5.1 Key wireframes

```
┌─ Home ───────────────────────────┐   ┌─ Question 37 / 180 ────── ⏱ 02:41:12 ┐
│ Good evening, Asha 👋            │   │ [Process · Agile]            ⚑ Mark  │
│ ┌──────────┐ Readiness           │   │                                      │
│ │   62 %   │ Study  14.5 h       │   │ Your team's velocity has dropped     │
│ │  (ring)  │ Lessons 18/42       │   │ for three sprints. The product owner │
│ └──────────┘ Last mock 68 %      │   │ asks you to commit more stories…     │
│ ▶ Continue: Stakeholder engage…  │   │                                      │
│ Today: 20 flashcards · 30-Q test │   │ ○ A. Ask the team to work overtime   │
│ Mock trend ▁▃▄▆▅▇                │   │ ● B. Facilitate a retrospective to…  │
│ Upcoming: Free PMI chapter webinar│  │ ○ C. Escalate to the sponsor         │
│                                  │   │ ○ D. Reduce the definition of done   │
├──────────────────────────────────┤   │                                      │
│ 🏠  📘  ✍️  ⏱  📚  👤            │   │ ◀ Prev     ▦ Palette      Next ▶     │
└──────────────────────────────────┘   └──────────────────────────────────────┘

┌─ Results ────────────────────────┐   ┌─ Review · Q12 (Incorrect) ───────────┐
│ Full Mock #2       Score 71 %    │   │ You chose C · Correct: B             │
│ Time used 3h 22m                 │   │ ✔ Why B: servant leadership…          │
│ People      ████████░░ Target    │   │ ✘ Why A: overtime is unsustainable…   │
│ Process     ██████████ Above     │   │ ✘ Why C: escalation is premature…     │
│ Business En ██████░░░░ Below     │   │ ✘ Why D: lowers quality…              │
│ Weak: Compliance, Benefits real. │   │ Concept: Team performance (ECO P-T3)  │
│ [Review answers] [Practise weak] │   │ [Open lesson] [Ask AI to explain]     │
└──────────────────────────────────┘   └──────────────────────────────────────┘
```

**Visual design:** Material 3 with a calm navy and teal palette and an amber accent for "marked" items. Inter or Roboto Flex type, 8-pt spacing. Light and dark themes are tested for contrast. In the exam player, the question text column is limited to about 70 characters per line for readability on tablets.

---

## 6. Database design (PostgreSQL / Supabase)

The full DDL will be in `supabase/migrations/`. Core tables:

```sql
-- Reference / content ------------------------------------------------------------
eco_versions(id PK text 'ECO-2026-07', title, effective_from date, source_url, is_current bool)
domains(id PK, eco_version FK, code 'PEOPLE'|'PROCESS'|'BUSINESS_ENV', name, weight_pct numeric, sort)
tasks(id PK, domain_id FK, code 'P-T1', title, description, sort)
lessons(id PK, task_id FK, title, body_md, key_terms jsonb, examples_md, est_minutes,
        status content_status, eco_version, version int, author_id, reviewer_id,
        published_at, updated_at)
flashcards(id PK, task_id FK, front, back, status, eco_version)
faqs(id PK, domain_id FK NULL, question, answer_md, status)
study_files(id PK, title, storage_path, licence, source_url, eco_version, status)  -- PDFs

questions(id PK uuid, type question_type, stem_md, scenario_md NULL,
          payload jsonb,        -- options / pairs / drag targets, see §7
          answer jsonb,         -- correct key(s) / mapping / order
          explanation_md, distractor_rationale jsonb, concept_refs text[],
          domain_id FK, task_id FK, approach 'PREDICTIVE'|'AGILE'|'HYBRID',
          difficulty smallint 1-5, eco_version,
          content_label 'DEMO'|'ORIGINAL_REVIEWED',   -- demo vs verified content
          status content_status, version int, author_id, reviewer_id,
          created_at, updated_at, published_at)
-- enum content_status: draft | in_review | approved | published | retired
-- enum question_type: MCQ_SINGLE | MCQ_MULTI | MATCHING | DRAG_ORDER | DRAG_CATEGORIZE | CASE_STUDY

exam_blueprints(id PK, name, eco_version, total_questions, duration_min,
                sections jsonb,      -- [{name, question_count, break_after_min}]
                domain_mix jsonb,    -- {"PEOPLE":33,"PROCESS":41,"BUSINESS_ENV":26}
                approach_mix jsonb,  -- {"PREDICTIVE":40,"AGILE_HYBRID":60}
                is_active bool)
mock_exams(id PK, blueprint_id FK, title, kind 'DEMO'|'FULL'|'FIXED',
           question_ids uuid[] NULL,  -- fixed form; NULL = generated from blueprint
           status, published_at)
content_releases(version int PK, published_at, notes)   -- drives app delta sync

-- Directory -----------------------------------------------------------------------
resources(id PK, category, title, provider, url, licence, cost 'FREE'|'FREE_REGISTRATION',
          description, last_verified_at, verified_by FK, status)
institutions(id PK, name, type 'PMI'|'PMI_CHAPTER'|'ATP'|'UNIVERSITY'|'TRAINER'|'OTHER',
             country, website, contact_public, description,
             partnership_status 'LISTED'|'IN_DISCUSSION'|'VERIFIED_PARTNER',
             partnership_evidence_path NULL, verified_at NULL, status)
events(id PK, institution_id FK NULL, title, starts_at, url, is_free bool, status)
partnership_enquiries(id PK, institution_name, contact_name, email, message,
                      created_at, handled_by FK NULL, state)

-- Users & learning -----------------------------------------------------------------
profiles(id PK = auth.users.id, display_name, country, exam_date date NULL,
         daily_goal_min, analytics_consent bool, created_at)
user_roles(user_id FK, role 'REVIEWER'|'CONTENT_ADMIN'|'DIRECTORY_ADMIN'|'SUPER_ADMIN')
attempts(id PK uuid, user_id FK, mode 'PRACTICE'|'MOCK', mock_exam_id NULL,
         blueprint_snapshot jsonb, started_at, submitted_at, duration_sec,
         score_pct numeric, domain_scores jsonb, auto_submitted bool, device_id)
attempt_answers(attempt_id FK, question_id FK, question_version int, response jsonb,
                is_correct bool, marked bool, time_spent_sec, PRIMARY KEY(attempt_id, question_id))
lesson_progress(user_id, lesson_id, completed_at, seconds_spent, PK(user_id, lesson_id))
flashcard_reviews(user_id, flashcard_id, ease, interval_days, due_at, PK(user_id, flashcard_id))
study_sessions(id PK, user_id, started_at, ended_at, activity)
feedback(id PK, user_id NULL, question_id NULL, kind 'ERROR'|'SUGGESTION'|'BUG', message, state)
ai_usage(user_id, day date, requests int, tokens int, PK(user_id, day))
audit_log(id PK, actor_id, table_name, row_id, action, diff jsonb, at)  -- trigger-written
```

### 6.1 Access control (RLS)
- Content tables: `SELECT` is allowed for everyone only where `status = 'published'`. Writes are allowed only for users holding a matching role in `user_roles`, checked by a `SECURITY DEFINER` function `has_role()`.
- Moving content to `published` requires `CONTENT_ADMIN`. A reviewer cannot approve content they wrote themselves (four-eyes rule, enforced by a trigger).
- Learner tables (`attempts`, `progress` and similar): each user can read and write only rows where `user_id = auth.uid()`. Admin reads for reports go through aggregated views only.
- `audit_log` is insert-only, written by triggers on every content table.
- `partnership_enquiries`: anyone can insert, with rate limits. Only `DIRECTORY_ADMIN` can read.

### 6.2 Local (Room) mirror
Room holds the published content tables plus the learner tables. Each local row has a `sync_state` column (`clean` / `dirty`). An exam in progress is written to Room after every answer and every 5 seconds of the timer, so a crash or a phone call never loses an attempt.

---

## 7. Question and exam engine

### 7.1 Item types (the `payload` and `answer` shapes)
| Type | Brief's term | Payload | Scoring |
|---|---|---|---|
| `MCQ_SINGLE` | Multiple choice, scenario-based, situational judgement | `options[{key,text}]` | Exact match |
| `MCQ_MULTI` | Multiple response | `options[]`, `select_count` | All correct keys and no wrong ones (PMI's practice is no partial credit) |
| `MATCHING` | Matching | `left[]`, `right[]` | All pairs correct. Partial match is shown in the review but counts as wrong. |
| `DRAG_ORDER` | Drag-and-drop (sequence) | `items[]` | Exact order |
| `DRAG_CATEGORIZE` | Drag-and-drop (buckets) | `items[]`, `buckets[]` | All items in the right bucket |
| `CASE_STUDY` | Practicum / case study | `case_md`, `exhibits[]` (tables, charts), `sub_questions[]` | Each sub-question is scored separately |

"Scenario-based" and "situational judgement" are **tags on top of a type**, not separate engines. Every drag-and-drop item also offers a tap-to-place mode for accessibility.

### 7.2 Exam session engine
- **Inputs:** a blueprint (sections, time, breaks, domain and approach mix) plus a question selector.
- **Selection:** stratified random sampling by domain weight, then by approach mix. Questions the learner saw recently are avoided. Option order is shuffled, except for "all of the above"-style items, which are flagged non-shuffleable.
- **Timer:** based on the monotonic clock (`SystemClock.elapsedRealtime`) so changing the device clock has no effect. Remaining time is persisted and restored. Warnings fire at 30, 10 and 5 minutes. When time runs out the exam **auto-submits**.
- **Sections and breaks:** for the 2026 format, the case-study section comes first, then break 1, then independent questions part A, then break 2, then part B. Once a section's break starts, that section is locked, as in the real exam. Breaks are optional and skippable.
- **Navigation:** Prev/Next, a palette with jump-to, mark for review, and a "review marked" filter, all within the current section.
- **Feedback modes:** *instant* (practice only) or *end of exam* (always used in mocks).
- **Results:** overall %, per-domain and per-approach %, PMI-style performance bands (thresholds are configurable and labelled as an *estimate*; PMI does not publish its cut score), time per question, and the weakest tasks.

### 7.3 Readiness score (dashboard)
Readiness = 0.25 × lesson coverage + 0.15 × flashcard retention + 0.25 × rolling practice accuracy (last 200 items) + 0.35 × average of the last 2 full-mock scores, with each domain weighted by the ECO weights. It is shown as a guide, never as a pass prediction.

---

## 8. Content strategy (legal and quality)

1. **All questions and notes are original.** They are written by the project against the public ECO task statements. Nothing is copied from the *PMBOK® Guide*, PMI's paid practice exams, or commercial prep books. Concepts are explained in our own words with our own examples.
2. **Demo vs verified.** Every item has `content_label`. `DEMO` means it was written during development and has not been SME-reviewed; it shows an amber "Demo content" chip. `ORIGINAL_REVIEWED` means a reviewer holding a PMP approved it. Full mocks used for readiness should draw only on reviewed items once enough exist.
3. **Initial seed bank (MVP):** at least 300 original questions. Distribution follows the ECO (about 100 People, 120 Process, 80 Business Environment) and about 40/60 predictive vs agile/hybrid. All six item types are included, plus 2 case studies. Also: 120 flashcards, 1 lesson per ECO task, and 30 FAQs. The full 180-question mock needs at least 180 eligible items; with 300, two mostly distinct forms can be generated.
4. **Resource library:** each link is added by an admin with its source, licence or cost note, and a `last_verified_at` date. A nightly job checks the links and flags any that break. Nothing is mirrored or re-hosted unless its licence allows it (for example CC-BY open educational resources). PMI's free public documents, such as the ECO PDF and the exam pages, are **linked, not re-hosted**.
5. **Institutions:** directory entries contain public information only (name, website, public contact). The badge shows **"Listed"** by default. **"Verified partner"** appears only after a Super Admin uploads written authorization (`partnership_evidence_path`). No partnerships are seeded; the MVP ships with a clearly labelled "Listed" directory only.
6. **Disclaimer** on onboarding, in About, and on every mock results screen: *"OpenPM Prep is an independent, free study platform. It is not affiliated with, endorsed by, or sponsored by Project Management Institute (PMI). PMP, PMBOK and PMI are registered marks of Project Management Institute, Inc."*

---

## 9. AI learning assistant (optional, v1.1)

- **Flow:** App → `ai-assistant` Edge Function (checks the JWT, quota and moderation) → LLM provider → response streamed back. **No AI key is ever in the APK.**
- **Grounding:** the system prompt includes the relevant lesson and the question's explanation, so answers stay consistent with app content. Each answer carries an "AI-generated, may be wrong" label.
- **Features:** explain a concept, explain my wrong answer (from Review), generate 5 practice questions on a weak task (marked *AI-generated, unreviewed*, never mixed into mocks), and build a study plan from the exam date and weak areas.
- **Quota:** 20 requests per learner per day by default, with a global daily budget cap that turns the feature off for the day once it is reached. Guests have no AI (it requires sign-in, to prevent abuse).
- **Provider:** pluggable through an environment variable. Option A: an open-weight model (for example a Llama-class model) on a low-cost inference host. Option B: a small Claude model (Haiku class). The quota keeps the worst-case monthly cost bounded (see §10).

---

## 10. Estimated operating costs

These are estimates in USD from public pricing as I understand it. Check them when the accounts are created.

| Item | Launch (≤ 5k MAU) | Growth (≈ 50k MAU) |
|---|---|---|
| Google Play developer account | **$25 one-time** | — |
| Supabase | **$0** (free tier: 500 MB DB, 1 GB storage, 50k MAU; projects pause after 7 days with no activity, so keep it warm or upgrade) | **$25/mo** Pro (8 GB DB, 100 GB storage, daily backups) |
| Admin web hosting (Cloudflare Pages/Netlify) | $0 | $0 |
| Firebase (FCM, Crashlytics) | $0 | $0 |
| Domain for privacy policy, admin and links | ~$12/yr | ~$12/yr |
| AI assistant (optional, capped) | $0–10/mo | $30–150/mo, set by the global cap |
| Transactional email (Supabase built-in or Resend free tier) | $0 | $0–20/mo |
| **Total** | **≈ $25 + $1/mo** | **≈ $60–200/mo** |

Bundling the question bank in the APK and using delta sync keeps egress and DB reads very low. That is the main reason the free tier can carry a large audience.

---

## 11. Development timeline

The plan runs phase by phase, with a test report after each phase. Calendar estimates assume one full-time developer.

| Phase | Scope | Est. duration | Exit criteria (tested) |
|---|---|---|---|
| 1 | Requirements, architecture, this blueprint | done → approval | Owner approves |
| 2 | Project scaffold, design system, navigation, auth (guest/email/Google), Home dashboard | 2 weeks | App builds; navigation and theme work; auth flows pass instrumented tests |
| 3 | Learn module: ECO structure, lessons, flashcards (SRS), revision, FAQ | 2 weeks | Content renders offline; progress tracked |
| 4 | Question bank schema, seed loader, question engine (6 types), practice tests 10/30/60 | 2.5 weeks | Scoring unit tests 100% on every type |
| 5 | Mock simulator: blueprints, sections, breaks, timer, palette, auto-submit, crash-resume | 2 weeks | Timer and resume tests; process-death test |
| 6 | Results, review, explanations, analytics, readiness, sync | 1.5 weeks | Domain scoring verified against fixtures |
| 7 | Resource library, institutions directory, enquiry form, webinars | 1 week | Badge logic tests; link checker job |
| 8 | Supabase migrations + RLS, admin web (content CRUD, review workflow, mock builder, directory, users and roles, feedback, exports) | 3 weeks | RLS policy tests (pgTAP); role matrix tests |
| 9 | Testing, accessibility, security review, performance, privacy and terms | 1.5 weeks | Test report; no high-severity findings |
| 10 | Signed APK/AAB, Play listing, deployment guide, maintenance plan | 1 week | Installable release build |
| | **Total** | **≈ 16–17 weeks** | |
| v1.1 | AI assistant, FCM notifications, PDF export, learner web app | +3–4 weeks | |

In this session I can produce the code, the original seed content and the admin panel much faster than these calendar estimates. The limiting factors are build infrastructure (§13.1), SME review of questions, and your account setup (Supabase, Firebase, Play Console).

---

## 12. MVP definition

**In the MVP:** guest and signed-in learners, all 6 tabs, full study module (notes, flashcards, revision, FAQ), all six item types, 10/30/60 practice, short demo and full 180/240 mock, timer with breaks and auto-submit, results and review with distractor rationales, analytics, readiness, verified resource library, institution directory with enquiry form, light and dark mode, cloud sync, admin dashboard with RBAC and review workflow, audit log, privacy policy and terms, account deletion, and at least 300 original seeded questions.

**After the MVP:** AI assistant, push notifications, downloadable PDF packs, learner web app, multilingual content, discussion or community features, and confirmed institutional partnerships (these need real agreements).

---

## 13. Risks, constraints and decisions needed

### 13.1 Build environment (blocker for APK generation in this cloud session)
This container can reach Maven Central, Google Maven and Gradle, but **`dl.google.com` is blocked**. The Android SDK (platform tools, build tools, platforms) is downloaded from there, so I cannot produce an APK here until one of these is done:
- **Option A (recommended):** allow `dl.google.com` in this cloud environment's network settings. I can propose that change for you to approve.
- **Option B:** I add a **GitHub Actions workflow** that builds the debug APK and the signed release AAB on GitHub's runners, which already have the Android SDK. You download the APK from the workflow run. I recommend adding this anyway for reproducible releases.

The admin web, Supabase SQL and unit tests for the pure-Kotlin question engine can all be built and tested here regardless.

### 13.2 Trademark and naming
"PMP", "PMI" and "PMBOK" are PMI registered marks. Google Play also rejects app names that imply an affiliation. Recommendation: use a neutral brand (for example *OpenPM Prep*) with a descriptive subtitle such as "Free practice for the PMP® exam" and the disclaimer in §8.6. Do not use PMI logos.

### 13.3 Content accuracy
Original questions need review by someone who holds a PMP. Until that happens, items are labelled `DEMO`. **Decision needed:** who will be the first SME reviewer(s)?

### 13.4 Secrets
The only key in the app is the Supabase **anon (public) key**. It is designed to be public and safe only because RLS is enforced. The service-role key, AI provider keys and the signing keystore live only in Supabase secrets and GitHub Actions secrets, never in the repository.

### 13.5 Repository location
This repository (`Wan-VACE`) currently holds an unrelated ML project and an office-automation app. I've put the PMP app under `pmp_prep_app/` so nothing existing is touched. A dedicated repository would be cleaner for Play releases and CI. **Decision needed:** keep it here or move it to a new repository?

### 13.6 Decisions requested before Phase 2
1. Approve **Supabase + Room + React admin** (§3), or ask for all-Firebase instead.
2. Approve the **app name** approach (§13.2) and suggest a name if you have one.
3. Approve **MVP scope** (§12), with the AI assistant in v1.1.
4. Choose the build route: **allow `dl.google.com`**, **GitHub Actions**, or both (§13.1).
5. Repository location (§13.5).
6. Do you already have Supabase, Firebase and Google Play Console accounts? (Not needed until Phase 8/10. Until then I'll use a local Supabase config and placeholders.)
