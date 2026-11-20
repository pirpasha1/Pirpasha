# Verification report: links, facts, certificates and gaps

**Date:** 20 November 2026 · **Content version after fixes:** ECO-2026-07, 100 questions

This report covers four checks, each against primary sources:
1. Every external link in the app: does it load, and is it what we say it is?
2. Every factual claim about the PMP exam: is it in PMI's official documents?
3. TLS certificates of the linked sites, and the app's own signing certificate.
4. Gaps against the original project brief.

---

## 1. Links (17 unique URLs on 10 hosts)

Method: each URL was fetched twice.
- **Direct HTTPS check** from the build machine (status, redirects, content type, page title).
- **Real-browser fetch** with no cache. This was needed because PMI, opentextbc.ca and BCcampus block automated datacenter clients with bot protection (HTTP 403 "Error | PMI" / "Just a moment…"). Those 403s are not dead links.

| URL | Direct | Browser | Content matches the app's description? |
|---|---|---|---|
| pmi.org/…/new-pmp-examination-content-outline-2026.pdf | 200 PDF | – | ✅ The July 2026 ECO (text checked, §2) |
| pmi.org/…/generic-certification-handbook.pdf | 200 PDF | – | ✅ "PMI Certification Handbook – revised June 2026" |
| pmi.org/…/project-management-professional-handbook.pdf | 200 PDF | – | ❌ **Outdated.** It contains the **January 2021** ECO (People 42%, Process 50%, Business Environment 8%). **Removed from the app.** |
| pmi.org/certifications/project-management-pmp/new-exam | 403 (bot block) | 200 | ✅ "Learn what the new PMP® exam, launched in July 2026, means for you" |
| pmi.org/learning/authorized-training-partners | 403 (bot block) | 200 | ✅ ATP program page |
| pmi.org/learning/webinars | 403 (bot block) | 200 | ⚠️ Webinars are labelled "Free for Members". The cost text was corrected to *Mostly free for PMI members (membership is paid)*. |
| pmi.org/membership/chapters | 403 (bot block) | 200 | ✅ "over 300 local chapters". The text was corrected: joining a chapter requires PMI membership. |
| pmi.org/ | 403 (bot block) | 200 | ✅ PMI homepage |
| projectmanagement.com/webinars/webinarmainondemand.cfm | 403 (bot block) | 200 | ⚠️ The filter shows **524 free / 1,941 premium** webinars. The cost text was corrected to state this. |
| scrumguides.org/scrum-guide.html | 200 | – | ✅ Scrum Guide (CC BY-SA 4.0) |
| kanbanguides.org/the-kanban-guide/ | 200 | – | ✅ The Kanban Guide (May 2025, latest) |
| agilemanifesto.org/ | 200 | – | ✅ |
| opentextbc.ca/projectmanagement/ | 403 (bot block) | 200 | ✅ Adrienne Watt, **CC BY 4.0** (licence quoted from the page) |
| collection.bccampus.ca/textbook/qG6YTBiy/ | 403 (bot block) | 200 | ✅ Same book, CC BY 4.0 |
| gac-dir.weaveaccreditation.com/ | 200 | 200 | ✅ "GAC – Global Accreditation Center" member directory. PMI's exam page links to it as "Browse GAC Programs". |
| scrum.org/ | 200 | – | ✅ |
| agilealliance.org/ (was www.) | redirect → apex | 200 | ⚠️ Agile Alliance **joined PMI in January 2025** (its memberships remain separate). The description was updated and the URL changed to the canonical apex domain. The free-glossary claim wasn't on the homepage, so the glossary page is now linked directly and verified. |

**Links added after verification (both checked live, 200):**
- `agilealliance.org/agile101/agile-glossary/` (Agile Glossary, free).
- `scrum.org/open-assessments`. The page says "Open Assessments have no fee". This also fills the empty "Sample questions" category.

**Result:** 18 links in the app, all live. 1 outdated link removed. 4 descriptions corrected.

---

## 2. Facts checked against PMI's official documents

Sources: the *PMP Examination Content Outline – July 2026* PDF and the *PMI Certification Handbook – revised June 2026*. The text was extracted from both PDFs and the claims below were checked line by line.

| Claim in the app | Official source says | Status |
|---|---|---|
| People 33%, Process 41%, Business Environment 26% | "DOMAIN I PEOPLE—33% … II PROCESS—41% … III BUSINESS ENVIRONMENT—26%" | ✅ |
| 26 task titles (8 / 10 / 8) | All 26 headings match **word for word** | ✅ |
| 180 questions, 170 scored + 10 pretest | Same | ✅ |
| 240 minutes | "The allotted time … is 240 minutes" | ✅ |
| Two 10-minute breaks: after the case-study section and about midway through the independent questions; the previous section can't be revisited | Same, almost word for word | ✅ |
| About 40% predictive, 60% agile or hybrid | "Approximately 40% … predictive" | ✅ |
| 35 hours of training required | "at least 35 hours of commercial training … aligned with … ECO" | ✅ |
| Practice apps don't count as training | "books and practice exams alone will NOT be accepted" | ✅ The FAQ now quotes this rule. |
| From 1 Dec 2026, live hours count only if delivered by an ATP, a China REP or an accredited academic program | PMI new-exam page (browser fetch) | ✅ Added precisely to the FAQ and the ATP entry |
| PMI doesn't publish a fixed passing percentage | "passing score … determined by sound psychometric analysis" | ✅ FAQ reworded: the app's bands are its own estimate |
| Up to 3 attempts within a 1-year eligibility period | Certification handbook | ✅ Added as a new FAQ |

---

## 3. Certificates

### 3a. TLS certificates of linked sites
The build machine's HTTPS proxy re-terminates TLS, so local checks would only see the proxy's certificate. Real served certificates were therefore taken from **Qualys SSL Labs** public scans.

| Host | Certificate CN | Issuer | Expires | Grade |
|---|---|---|---|---|
| www.pmi.org | pmi.org | YE1 (a Let's Encrypt 2025 intermediate; short-lived, auto-renewing) | 2026-12-24 | A+ (4 endpoints) |
| www.projectmanagement.com | projectmanagement.com | YE2 (a Let's Encrypt 2025 intermediate; short-lived, auto-renewing) | 2027-01-13 | A+ (4 endpoints) |
| kanbanguides.org | kanbanguides.org | GeoTrust TLS RSA CA G1 | 2027-05-05 | A |
| agilealliance.org | agilealliance.org | YR2 (a Let's Encrypt 2025 intermediate; short-lived, auto-renewing) | 2026-12-22 | A |
| www.scrum.org | scrum.org | Amazon RSA 2048 M04 | 2027-04-07 | A+ (4 endpoints) |
| scrumguides.org | scrumguides.org | YR1 (Let's Encrypt) | 2027-01-22 | B (4 endpoints) ¹ |
| agilemanifesto.org | agilemanifesto.org | YR1 (Let's Encrypt) | 2027-01-27 | B (4 endpoints) ¹ |
| opentextbc.ca | opentextbc.ca | WR1 (Google Trust Services) | 2027-01-20 | A (6 endpoints) |
| collection.bccampus.ca | bccampus.ca | WR1 (Google Trust Services) | 2027-01-20 | A+ (6 endpoints) |
| gac-dir.weaveaccreditation.com | *.weaveaccreditation.com | Amazon RSA 2048 S24 | 2027-06-02 | A+ (12 endpoints) |

¹ The B grade is a server-configuration cap, not a certificate problem. These two sites are on GitHub Pages' shared servers (185.199.108–111.153). The certificate is valid and trusted, only TLS 1.2 and 1.3 are offered, and there is no RC4 or BEAST exposure. SSL Labs caps the grade because only some cipher suites provide forward secrecy (its forward-secrecy rating is 1) and HSTS is absent. Visitors' connections are still encrypted and authenticated; the owners would need to change this on their side.

The pmi.org and agilealliance.org certificates expire within ~5 weeks. That is normal for 90-day auto-renewing certificates, and the sites will renew them themselves. The app only opens these links in the phone's browser, which does its own certificate checks.

### 3b. App signing certificate
| APK | Signature | Certificate |
|---|---|---|
| `OpenPMPrep-0.1.0-debug.apk` (sent to you) | ✅ Verifies (APK Signature Scheme v2) | `CN=Android Debug, O=Android, C=US` · SHA-256 `a721eec6…f395ae98` · valid until 2056 |
| `app-release-unsigned.apk` | Unsigned (expected) | Must be signed with your private release key before Play Store upload (Phase 10) |

**Fix applied:** that debug key was generated inside a temporary cloud machine, so a future rebuild would have produced a differently signed APK. That would force an uninstall, wiping a learner's local progress. The same key is now committed as `android/app/debug.keystore` (debug keys are not secret) and pinned in the build. The rebuilt APK has the identical SHA-256 fingerprint, so it installs as an update.

### 3c. Remaining TLS scans
All 10 hosts are now scanned (final poll at 02:15 UTC, 20 Nov 2026).
- **Result:** every certificate is valid, trusted, covers its hostname and is in date.
- **Grades:** 6 × A+, 2 × A, 2 × B. The B grades are server cipher configuration only (see footnote ¹).
- **Earliest expiries:** agilealliance.org (22 Dec 2026) and pmi.org (24 Dec 2026). Both use short-lived certificates from automatically renewing authorities.
- **Re-check:** repeat this check at each content release.

---

## 4. Gaps against the original brief

### Content gaps (found and partly closed)
| Gap | Before | After this pass | Still open |
|---|---|---|---|
| Question count | 88 | **100** (+12 new original questions) | Target ≥ 300; 180 needed for a full-length mock |
| Predictive share (exam ≈ 40%) | 57% | **50%** | Add more agile and hybrid items to reach ~40% |
| New 2026 themes (AI, sustainability) | 2 + 2 questions | **5 AI + 3 sustainability** | Lessons could expand on these too |
| Thinnest tasks (2 questions each) | 7 tasks | Every task now has ≥ 3 questions | Aim for ≥ 8 per task |
| Free sample-question resources | none | Scrum Open Assessments | No PMI-provided free PMP sample test was found to link. PMI's practice exam is paid, so it is not listed. |
| SME review | 0% reviewed | 0% reviewed | **Needs a PMP-certified reviewer** (owner decision) |

### Feature gaps against the brief
| Brief item | Status |
|---|---|
| Email and Google login | ❌ Phase 8 (backend) |
| Cloud sync, admin dashboard, role-based access, audit, report export | ❌ Phase 8 |
| Push notifications (FCM) | ❌ v1.1 |
| AI learning assistant | ❌ v1.1 (designed: server-side key, quotas) |
| Downloadable PDF study packs | ❌ v1.1. Official PDFs are linked. |
| Webinar/event listings with dates | ⚠️ Linked to webinar libraries only; dated events need the admin panel (Phase 8) |
| Partnership enquiries delivered to admins | ⚠️ Stored on the device until Phase 8 |
| Real-device / emulator testing | ⚠️ Not possible on this machine (no KVM); planned for Phase 9 |
| Legal review of privacy policy and terms | ⚠️ Drafts, marked as such in the app |
| Institutional partnerships | ✅ Correctly none claimed. All entries say "Listed – not a partner". |

---

## 5. Tests after all fixes
- Engine and content tests: **23/23 pass**. `ContentTest` validates the new 100-question bundle.
- End-to-end app flows (Robolectric): **4/4 pass**.
- Debug and release builds: ✅
