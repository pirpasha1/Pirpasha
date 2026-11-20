# Publishing guide: download link, Google Play and other Android stores

*Checked against official sources on 20 November 2026. Store rules change often, so re-check the linked pages before you submit.*

---

## 0. Direct download (test build, available now)

Each tested build is published as a **GitHub pre-release**:

- Release page: https://github.com/pirpasha1/Pirpasha/releases
- Direct link for this version: https://github.com/pirpasha1/Pirpasha/releases/download/pmp-v0.1.2-mvp/OpenPMPrep-0.1.2-mvp-test.apk

**To install on a phone (Android 8.0 or newer):**
1. Open the link on the phone and download the `.apk`.
2. When asked, allow your browser or Files app to **"Install unknown apps"**.
3. Tap the file, then tap **Install**.

Notes:
- This is a **test build** signed with a debug key, which is fine for sideloading. Play Store uploads need the release bundle described in step 2.
- **Android developer verification:** from **30 September 2026**, certified Android devices in Brazil, Indonesia, Singapore and Thailand block installs of apps whose developer isn't verified. Google plans to extend this **worldwide in 2027**. Sideloading works elsewhere for now. Before 2027, register as a developer and register the package name `org.openpm.prep` in the Android Developer Console (https://developer.android.com/developer-verification).

---

## 1. Google Play: one-time setup

| Step | What to do |
|---|---|
| 1.1 | Create a Play Console developer account at https://play.google.com/console. There is a one-time registration fee (US$25 at the time of writing). You'll need identity verification. Choose **Organization** if you have a registered entity (e.g. a non-profit or company); otherwise **Personal**. |
| 1.2 | **Personal accounts created after 13 Nov 2023:** before you can publish to production, you must run a **closed test with at least 12 testers who stay opted in for 14 days in a row**. Start recruiting testers early, e.g. PMP study groups or colleagues. Source: https://support.google.com/googleplay/android-developer/answer/14151465 |
| 1.3 | Have ready: support email, privacy-policy URL (step 3), the store graphics in `docs/store/`, the screenshots in `docs/screenshots/`, and the listing text in `docs/STORE_LISTING.md`. |

**Already handled in the app:**
- ✅ **Target API level:** since **31 Aug 2026**, new apps must target **Android 16 (API 36)**. Version 0.1.2 targets API 36. (https://support.google.com/googleplay/android-developer/answer/11926878)
- ✅ **App Bundle (.aab)** format: the build produces one.
- ✅ **No data collected:** there's no internet permission and no SDKs, which keeps the Data Safety form simple.

---

## 2. Create your upload key and build the signed bundle

You create the key **on your own computer**. Never share it, email it or commit it.

```bash
keytool -genkeypair -v -keystore openpm-upload.jks -alias upload \
        -keyalg RSA -keysize 4096 -validity 10000
```
Store the `.jks` file and both passwords in a password manager **and** an offline backup.

**Option A: let GitHub build it (recommended).** In GitHub, go to **Settings → Secrets and variables → Actions → New repository secret** and add four secrets:

| Secret | Value |
|---|---|
| `UPLOAD_KEYSTORE_BASE64` | output of `base64 -w0 openpm-upload.jks` (macOS: `base64 -i openpm-upload.jks`) |
| `UPLOAD_STORE_PASSWORD` | the keystore password |
| `UPLOAD_KEY_ALIAS` | `upload` |
| `UPLOAD_KEY_PASSWORD` | the key password |

The next workflow run will produce an artifact named **`openpm-prep-store-release`** containing `app-release.aab` and a signed `app-release.apk`. Download it from the run's **Summary** page.

**Option B: build locally.** Create `pmp_prep_app/android/keystore.properties`; this file is git-ignored:
```
storeFile=/full/path/to/openpm-upload.jks
storePassword=…
keyAlias=upload
keyPassword=…
```
Then run `./gradlew :app:bundleRelease`. The output is `app/build/outputs/bundle/release/app-release.aab`.

When you upload the first bundle, Play will offer **Play App Signing**. Accept it: Google keeps the final app-signing key, and your upload key can be reset if it's ever lost.

**Before each new upload:** increase `versionCode` (and `versionName`) in `app/build.gradle.kts`. Play rejects a versionCode it has already seen.

---

## 3. Publish the privacy policy at a public URL

Play requires a public, non-PDF web page. The text is ready in `docs/PRIVACY_POLICY.md`. Add your support email, then publish it in one of these ways:
- **Simplest:** use the GitHub file URL once the branch is merged into the default branch: `https://github.com/pirpasha1/Pirpasha/blob/<default-branch>/pmp_prep_app/docs/PRIVACY_POLICY.md`
- **Cleaner:** enable GitHub Pages, or use a small website or free page builder.

---

## 4. Create the app in Play Console

1. **Create app:** name `OpenPM Prep`, language, **App**, **Free**. Accept the declarations. Note that a free app can never be changed to paid later.
2. **Dashboard → Set up your app.** Complete each item:

| Section | What to enter for this app |
|---|---|
| Privacy policy | URL from step 3 |
| App access | "All functionality is available without special access" (no login) |
| Ads | "No, my app does not contain ads" |
| Content rating | Fill in the IARC questionnaire: category Education/Reference, no violence, sexual content, gambling, user-generated content or chat. You should get the lowest rating. |
| Target audience | 18 and over (adult professionals). This avoids the Families-policy requirements. |
| News app | No |
| Data safety | "Does your app collect or share any of the required user data types?" → **No**. Data is encrypted in transit → not applicable (nothing is transmitted). Account deletion → not applicable (no accounts). Re-do this form when you add accounts or sync. |
| Government app | No |
| Financial features | None |
| Health | None |

3. **Main store listing:** paste the text from `STORE_LISTING.md`. Upload `docs/store/icon-512.png`, `docs/store/feature-graphic-1024x500.png` and 2–8 screenshots. Category: Education. Add your contact email.
4. **Countries:** choose all, or only the regions you plan to support.

---

## 5. Testing tracks, then production

1. **Internal testing (optional, instant):** upload `app-release.aab` and add your own Google account. This is a good way to check the release build on your phone.
2. **Closed testing (required for new personal accounts):**
   - create the track, upload the same `.aab`, and add at least 12 testers (an email list or Google Group);
   - share the opt-in link and make sure each tester **accepts the invitation and installs the app**;
   - keep at least 12 opted in for **14 consecutive days**;
   - collect feedback and fix issues; you'll be asked about this.
3. **Apply for production:** after 14 days, go to **Dashboard → Apply for production** and answer the questions about your test.
4. **Release to production:** create a release on the Production track, upload the `.aab`, add release notes, then **Send for review**. Reviews typically take from a few days to a week or more for new accounts.

**Common rejection risks for this app, and how to avoid them:**
- **Trademark / impersonation:**
  - Keep the name free of "PMP"/"PMI";
  - keep the disclaimer in the description (it is already in the provided text);
  - don't use PMI logos.
- **Misleading claims:** don't claim official status, guaranteed passing, or "real exam questions".
- **Broken functionality:** reviewers run the app. Test the release build on a real phone first (Phase 9).

---

## 6. Other Android app stores

| Store | Status / fit for this app | How |
|---|---|---|
| **Samsung Galaxy Store** | ✅ Good second store; reaches Samsung phones | Create a Samsung account and register at the Seller Portal (https://seller.samsungapps.com/). Samsung states that **commercial seller status is required even for free apps**. Then **Add New App**: upload the signed release **APK**, add the description, age rating, screenshots and privacy-policy URL, and submit for review. |
| **Huawei AppGallery** | ⚠️ Useful only if you target Huawei phones sold without Google services | Register at the Huawei Developer console (https://developer.huawei.com/consumer/en/), verify your identity, create the app in **AppGallery Connect**, upload the signed APK/AAB and listing, then submit for review. Check their current verification rules for your country. |
| **F-Droid** (free & open-source store) | ⚠️ Possible later. Requires a clear open-source licence for `pmp_prep_app/`; F-Droid builds the app from source. | Choose and add a licence (e.g. Apache-2.0 for code, CC BY 4.0 for content), then open a request at https://gitlab.com/fdroid/fdroiddata. |
| **Amazon Appstore** | ❌ Not for phones. Amazon **discontinued its Appstore on Android devices on 20 August 2025**; it remains only on Fire tablets and Fire TV. | Skip, unless you specifically want Fire tablets. |
| **Your own website / GitHub Releases** | ✅ Available now (step 0) | Subject to the developer-verification rollout described in step 0. |

**Use the same signing key in every store.** If the same package name is signed with different keys in different stores, users can't update across stores.

---

## 7. Release checklist

- [ ] Real-device test of the release build (Phase 9)
- [ ] Privacy policy and terms reviewed by a lawyer; support email added
- [ ] Upload key created and backed up; GitHub secrets added
- [ ] `versionCode` incremented
- [ ] Data Safety and content rating completed
- [ ] 12 testers × 14 days of closed testing (personal accounts)
- [ ] Screenshots, icon and feature graphic uploaded
- [ ] Android Developer Console registration (developer verification) before 2027
