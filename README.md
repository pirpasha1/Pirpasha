# CallGuard Local

Free, offline auto-reply and call helper for Android. No account, no cloud, **no internet permission**.

## Get the APK (pick one)

**A. GitHub builds it for you (free, no installs)**
1. Create a private GitHub repo and upload this whole folder (keep `.github/` and `tests/`).
2. Open **Actions → Build APK → Run workflow** (it also runs on every push).
3. When it turns green, open the run and download **CallGuardLocal-debug-apk**. Unzip, copy `app-debug.apk` to your phone.
4. If the build fails, open the failed step, copy the red error text, and send it to me; I will fix the code.

**B. Android Studio**: *File → Open* this folder → wait for Gradle sync → *Build → Build APK(s)*.
Output: `app/build/outputs/apk/debug/app-debug.apk`.

## First-time setup on the phone
1. Install the APK (allow "install unknown apps" for your file manager/browser).
2. Open the app → **Grant permissions**.
3. **WhatsApp:** tap *Allow WhatsApp reading* and enable CallGuard Local. On Android 13+ you may first need
   *Settings → Apps → CallGuard Local → ⋮ → Allow restricted settings*.
4. **Call blocking (optional):** tap *Enable call blocking* and choose CallGuard Local.
5. Edit your reply templates, switch on the channels you want, press **SAVE SETTINGS**.
6. Send yourself a test from another number and check the *Activity log*.
7. Disable battery optimisation for the app (Settings → Apps → CallGuard Local → Battery → Unrestricted), otherwise some phones kill it.

## What it does
| Feature | How |
|---|---|
| SMS auto-reply | Receives SMS, replies from your template, once per person per cool-down (default 30 min) |
| Missed-call reply | Detects ringing → not answered → sends your template by SMS |
| WhatsApp / WhatsApp Business auto-reply | Presses the notification's own Reply action. 1-to-1 chats only; groups are skipped |
| "Urgent" smart reply | If the incoming text says urgent/emergency/asap/immediately, uses your urgent template (rule based, not cloud AI) |
| Contacts-only mode | Reply only to saved contacts |
| Block list | Rejects incoming calls from numbers you block; blocked numbers never get a reply |
| Call recording | Best effort, see limits. Saved only in the app's private folder, with a visible notification |
| Local storage | Settings in private SharedPreferences, log/blocklist in private SQLite. Message text is never stored |

## Privacy guard (what stops leaks)
* Replies are built **only from your templates**. The incoming message is never copied into a reply.
* Every reply is scanned before sending. Blocked by default: card numbers (Luhn), Aadhaar (Verhoeff), PAN, IFSC, GSTIN,
  passport, bank/account numbers, UPI IDs, e-mail, phone numbers, OTP/CVV/PIN/password words, 6-8 digit codes,
  money amounts, salary/loan/balance words, addresses/DOB words, links, digits spelled out, and Devanagari/Gujarati/
  full-width/zero-width digit tricks.
* A template containing any of these cannot even be saved, and if one slips in at send time it is logged as BLOCKED and not sent.
* **Allow-list:** exact strings you type (e.g. an office e-mail) pass through; everything else stays blocked.
* No reply to bank/service short-code senders, OTP/transaction messages, or messages containing links.

## Tests and backtest
Run `./tests/run_tests.sh` (needs only a JDK). Latest result: 30,000 generated sensitive messages (cards, Aadhaar, PAN, IFSC,
UPI, e-mail, mobile, accounts, OTP and password sentences) → 30,000 blocked; 6,000 benign replies → 0 false positives;
plus unit, evasion, allow-list and end-to-end inbox simulations, all passing.
Known gaps: letters spaced out like `P I N` or `O.T.P` are not detected (only matters if you type that in a template yourself).

## Honest limits
* **Call recording:** Android 10+ blocks third-party apps from the other person's voice. Expect your own voice, or both
  sides only on speakerphone. Android 12+ may refuse to start the microphone from the background; the log then shows
  RECORD_FAILED. Use *Record now* in the app, or your phone dialer's built-in recorder if it has one.
  Uninstalling the app deletes its recordings.
* **Truecaller-style spam database:** impossible offline and free. This app has your own block list and contact checks only.
* Recording or auto-replying on behalf of someone has legal and courtesy aspects. Tell people you record calls.
* The Android part could not be compiled in my sandbox (no access to Google's build servers). The core logic is tested;
  the first GitHub/Android Studio build is the real compile check.
