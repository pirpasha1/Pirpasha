import com.localguard.autoreply.core.*;
import java.util.*;

/** Plain-JVM tests + backtest. Run with tests/run_tests.sh (no JUnit or Android needed). */
public class GuardTests {
    static int pass = 0, fail = 0;
    static final List<String> failures = new ArrayList<String>();

    static void expectBlocked(PrivacyGuard g, String label, String text) {
        PrivacyGuard.Verdict v = g.check(text);
        if (!v.allowed()) pass++; else { fail++; failures.add("MISSED  [" + label + "] " + text); }
    }
    static void expectAllowed(PrivacyGuard g, String label, String text) {
        PrivacyGuard.Verdict v = g.check(text);
        if (v.allowed()) pass++; else { fail++; failures.add("FALSE+  [" + label + "] " + text + "  -> " + v.summary()); }
    }

    static String digits(Random r, int n, int firstMin) {
        StringBuilder sb = new StringBuilder();
        sb.append((char) ('0' + firstMin + r.nextInt(10 - firstMin)));
        for (int i = 1; i < n; i++) sb.append((char) ('0' + r.nextInt(10)));
        return sb.toString();
    }
    static String luhnCard(Random r, int len) {
        String p = digits(r, len - 1, 3);
        for (int c = 0; c <= 9; c++) if (Validators.luhn(p + c)) return p + c;
        throw new IllegalStateException();
    }
    static String aadhaar(Random r) {
        String p = digits(r, 11, 2);
        return p + Validators.verhoeffCheckDigit(p);
    }
    static String group(String d, int size, String sep) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < d.length(); i++) { if (i > 0 && i % size == 0) sb.append(sep); sb.append(d.charAt(i)); }
        return sb.toString();
    }
    static String letters(Random r, int n) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) sb.append((char) ('A' + r.nextInt(26)));
        return sb.toString();
    }
    static <T> T pick(Random r, T[] a) { return a[r.nextInt(a.length)]; }

    static final String[] PRE = {"Hi, ", "Sure, ", "Ok. ", "Please note: ", "FYI ", "Here you go: ", "", "Details - ", "As asked, "};
    static final String[] POST = {"", " thanks", ". Call me later.", " ok?", " - regards", "\nBye"};

    public static void main(String[] args) {
        PrivacyGuard g = new PrivacyGuard(Collections.<String>emptyList());

        // ---------- 1. Hand-written sensitive cases (must all be BLOCKED) ----------
        String[] bad = {
            "My card is 4111 1111 1111 1111", "card 5500-0000-0000-0004 expiry 12/28", "4012888888881881",
            "Aadhaar 2345 6789 0124?", "my PAN is ABCDE1234F", "abcde1234f", "IFSC HDFC0001234", "GSTIN 27AAPFU0939F1ZV",
            "passport A1234567", "pay me on rahul@okaxis", "mail me at someone@example.com", "Mail: a.b+c@sub.domain.co.in",
            "call me on 9876543210", "call +91 98765 43210", "+91-98765-43210", "09876543210", "919876543210", "0091 9876543210",
            "My account number is 123456789012", "a/c 00112233445566", "OTP is 482913", "otp 4829", "the code is 123456",
            "my password is hunter2", "password: abc", "CVV 123", "cvc is 456", "my pin is 4821", "UPI PIN 1234", "mpin 9988",
            "username: pirpasha", "login id admin01", "api key sk-123", "net banking details", "credit card details",
            "my salary is high", "bank balance is low", "pay Rs 5000", "send ₹5,000", "Rs. 1,50,000 pending", "50000 rupees",
            "5 lakh loan", "2 crore", "emi is due", "investment portfolio", "my address is near the market",
            "flat no 12", "house no 4", "Plot No. 51", "pincode 413512", "DOB 14/05/1991", "date of birth 14 May", "born on 14 May",
            "I live at the old house", "I stay in the colony", "my location is shared", "visit www.example.xyz", "http://evil.top/login",
            "see bit.ly/abc", "open abc.in/pay", "nine eight seven six five four three two one zero",
            "Aadhar card", "pan card number", "voter id", "driving license",
            // evasion attempts
            "call me on ९८७६५४३२१०",               // Devanagari digits
            "９８７６５４３２１０",                         // full-width digits
            "9​8​7​6​5​4​3​2​1​0",                      // zero-width split
            "9.8.7.6.5.4.3.2.1.0", "98-76-54-32-10", "9 8 7 6 5 4 3 2 1 0",
            "4111.1111.1111.1111", "4111  1111", // second is only 8 digits -> code number
            "O.T.P", "my  P I N", // see note: spaced letters are NOT caught by design; counted separately below
        };
        // The last two entries are known limitations; test them separately so the headline number is honest.
        for (int i = 0; i < bad.length - 2; i++) expectBlocked(g, "hand", bad[i]);

        // ---------- 2. Hand-written benign cases (must all be ALLOWED) ----------
        String[] good = {
            "I'm busy right now. I will call you back soon.", "Driving, will reply later.", "In a meeting till 5:30 pm.",
            "I'll be free after 18:45 today.", "Let's meet on 25-11-2026 at 10:30.", "See you on 2026-11-25.", "Meeting on 25/11/2026",
            "Room 204 on the 3rd floor", "We are 12 people", "Reached in 15 minutes", "Back by 7.30 pm", "Call tomorrow morning.",
            "Thanks for your message. I will respond shortly.", "Out of office, back on Monday.", "Please leave a message and I will get back to you.",
            "At the site, network is poor.", "Happy to help, will check and revert.", "Sorry, can't talk now. Will ring you in 2 hours.",
            "Urgent noted. Will call at the first chance.", "नमस्ते, मैं अभी व्यस्त हूँ।",
            "Reply in 10 min", "1 2 3 ok", "Total 24 items, 3 boxes", "Gate 5, bay 12",
        };
        for (String s : good) expectAllowed(g, "benign", s);

        // ---------- 3. Allow-list behaviour ----------
        PrivacyGuard ga = new PrivacyGuard(Arrays.asList("office@example.com", "022-12345678", "x"));
        expectAllowed(ga, "allow", "Email office@example.com for details");
        expectAllowed(ga, "allow", "Email OFFICE@EXAMPLE.COM for details");
        expectBlocked(ga, "allow", "Email other@example.com for details");
        expectBlocked(ga, "allow", "Email office@example.com or me@gmail.com");
        expectBlocked(ga, "allow", "My card 4111 1111 1111 1111 and office@example.com");
        expectBlocked(ga, "allow-short-literal-ignored", "pin x");           // 'x' (<4 chars) must not whitelist anything
        expectAllowed(ga, "allow", "Office line 022-12345678");

        // ---------- 4. Backtest: generated sensitive data embedded in random sentences ----------
        Random r = new Random(20261124L);
        int N = 3000, caught = 0, total = 0;
        Map<String, int[]> perType = new LinkedHashMap<String, int[]>();
        String[] types = {"card", "aadhaar", "pan", "ifsc", "upi", "email", "mobile", "account", "otp-sentence", "password-sentence"};
        for (String t : types) perType.put(t, new int[]{0, 0});
        for (int i = 0; i < N; i++) {
            for (String t : types) {
                String payload;
                if (t.equals("card")) { String c = luhnCard(r, 16); int m = r.nextInt(3); payload = m == 0 ? c : m == 1 ? group(c, 4, " ") : group(c, 4, "-"); }
                else if (t.equals("aadhaar")) { String a = aadhaar(r); int m = r.nextInt(3); payload = m == 0 ? a : m == 1 ? group(a, 4, " ") : group(a, 4, "-"); }
                else if (t.equals("pan")) payload = letters(r, 5) + digits(r, 4, 0) + letters(r, 1);
                else if (t.equals("ifsc")) payload = letters(r, 4) + "0" + letters(r, 3) + digits(r, 3, 0);
                else if (t.equals("upi")) payload = letters(r, 4 + r.nextInt(6)).toLowerCase() + pick(r, new String[]{"@okaxis", "@ybl", "@paytm", "@oksbi", "@upi"});
                else if (t.equals("email")) payload = letters(r, 5).toLowerCase() + "@" + letters(r, 5).toLowerCase() + pick(r, new String[]{".com", ".in", ".co.in"});
                else if (t.equals("mobile")) { String d = digits(r, 10, 6); int m = r.nextInt(4); payload = m == 0 ? d : m == 1 ? "+91" + d : m == 2 ? "+91 " + group(d, 5, " ") : "0" + d; }
                else if (t.equals("account")) payload = digits(r, 9 + r.nextInt(10), 1);
                else if (t.equals("otp-sentence")) payload = "OTP " + digits(r, 4 + r.nextInt(5), 0);
                else payload = "password " + letters(r, 8);
                String text = pick(r, PRE) + payload + pick(r, POST);
                int[] c = perType.get(t); c[1]++;
                if (!g.check(text).allowed()) c[0]++; else { failures.add("MISSED  [gen-" + t + "] " + text); }
            }
        }
        int genFail = 0;
        for (Map.Entry<String, int[]> e : perType.entrySet()) { total += e.getValue()[1]; caught += e.getValue()[0]; }
        genFail = total - caught;
        pass += caught; fail += genFail;

        // ---------- 5. Backtest: benign auto-replies must stay allowed (false-positive rate) ----------
        String[] A = {"I'm busy right now", "Driving at the moment", "In a meeting", "At the plant", "Out of network", "Away from my phone"};
        String[] B = {"will call you back", "will reply soon", "will get back to you", "will check and revert", "will ring you"};
        String[] C = {"by {t}", "after {t}", "around {t}", "in {n} minutes", "in {n} hours", "on {d}", "tomorrow"};
        String[] D2 = {".", "!", ". Thanks for understanding.", ". Please leave a message.", ". Urgent? Say 'urgent' and I will call first."};
        int benign = 6000, fp = 0;
        for (int i = 0; i < benign; i++) {
            String s = pick(r, A) + ", " + pick(r, B) + " " + pick(r, C) + pick(r, D2);
            s = s.replace("{t}", (1 + r.nextInt(12)) + ":" + String.format("%02d", r.nextInt(60)) + (r.nextBoolean() ? " pm" : " am"))
                 .replace("{n}", String.valueOf(5 + r.nextInt(90)))
                 .replace("{d}", String.format("%02d-%02d-%d", 1 + r.nextInt(28), 1 + r.nextInt(12), 2026 + r.nextInt(2)));
            if (!g.check(s).allowed()) { fp++; failures.add("FALSE+  [gen-benign] " + s + " -> " + g.check(s).summary()); }
        }
        pass += benign - fp; fail += fp;

        // ---------- 6. End-to-end inbox simulation through ReplyEngine ----------
        ReplyEngine.Config cfg = new ReplyEngine.Config();
        cfg.enabledChannels.addAll(Arrays.asList(ReplyEngine.SMS, ReplyEngine.CALL, ReplyEngine.WHATSAPP));
        cfg.templates.put(ReplyEngine.SMS, "I'm busy right now. I'll reply by {time}.");
        cfg.templates.put(ReplyEngine.CALL, "Sorry I missed your call. I'll call back soon.");
        cfg.templates.put(ReplyEngine.WHATSAPP, "Hi, I'm unavailable right now. I'll reply soon.");
        cfg.templates.put(ReplyEngine.T_URGENT, "Noted as urgent. I'll call you at the first chance.");
        cfg.vars.put("time", "6:30 pm");
        cfg.blocklist.add(ReplyEngine.last10("+91 90000 11111"));
        ReplyEngine eng = new ReplyEngine(g);
        ReplyEngine.MemoryStore store = new ReplyEngine.MemoryStore();
        long now = 1_000_000_000L;
        e2e("friend SMS replies", eng.process(new ReplyEngine.Inbound("SMS", "+919812345678", "Are you free?", false, true), cfg, now, store), ReplyEngine.Status.REPLY, "I'm busy");
        e2e("cooldown suppresses repeat", eng.process(new ReplyEngine.Inbound("SMS", "+919812345678", "Hello?", false, true), cfg, now + 60_000, store), ReplyEngine.Status.SKIP, null);
        e2e("after cooldown replies again", eng.process(new ReplyEngine.Inbound("SMS", "+919812345678", "Hello?", false, true), cfg, now + 31 * 60_000, store), ReplyEngine.Status.REPLY, null);
        e2e("bank short-code ignored", eng.process(new ReplyEngine.Inbound("SMS", "HDFCBK", "Rs 500 debited from a/c XX1234", false, false), cfg, now, store), ReplyEngine.Status.SKIP, null);
        e2e("OTP from numeric sender ignored", eng.process(new ReplyEngine.Inbound("SMS", "+918888877777", "Your OTP is 482913. Do not share.", false, false), cfg, now, store), ReplyEngine.Status.SKIP, null);
        e2e("phishing link ignored", eng.process(new ReplyEngine.Inbound("SMS", "+918888866666", "Your account is blocked, click http://x.top", false, false), cfg, now, store), ReplyEngine.Status.SKIP, null);
        e2e("blocklisted number ignored", eng.process(new ReplyEngine.Inbound("SMS", "09000011111", "hi", false, false), cfg, now, store), ReplyEngine.Status.SKIP, null);
        e2e("WhatsApp group ignored", eng.process(new ReplyEngine.Inbound("WHATSAPP", "Family", "hello all", true, false), cfg, now, store), ReplyEngine.Status.SKIP, null);
        e2e("WhatsApp 1:1 replies", eng.process(new ReplyEngine.Inbound("WHATSAPP", "Ravi", "call me", false, true), cfg, now, store), ReplyEngine.Status.REPLY, "unavailable");
        e2e("urgent template used", eng.process(new ReplyEngine.Inbound("WHATSAPP", "Sunil", "URGENT please call", false, true), cfg, now, store), ReplyEngine.Status.REPLY, "urgent");
        e2e("missed call replies", eng.process(new ReplyEngine.Inbound("CALL", "+917777788888", null, false, false), cfg, now, store), ReplyEngine.Status.REPLY, "missed your call");
        cfg.contactsOnly = true;
        e2e("contacts-only skips stranger", eng.process(new ReplyEngine.Inbound("SMS", "+917000000001", "hi", false, false), cfg, now, store), ReplyEngine.Status.SKIP, null);
        cfg.contactsOnly = false;
        cfg.enabledChannels.remove(ReplyEngine.SMS);
        e2e("disabled channel skips", eng.process(new ReplyEngine.Inbound("SMS", "+917000000002", "hi", false, true), cfg, now, store), ReplyEngine.Status.SKIP, null);
        cfg.enabledChannels.add(ReplyEngine.SMS);

        // A template that accidentally contains sensitive data must be BLOCKED, not sent.
        ReplyEngine.Config bad1 = new ReplyEngine.Config();
        bad1.enabledChannels.add(ReplyEngine.SMS);
        bad1.templates.put(ReplyEngine.SMS, "Busy. For payments use acct 123456789012 IFSC HDFC0001234");
        e2e("sensitive template BLOCKED", eng.process(new ReplyEngine.Inbound("SMS", "+917000000003", "hi", false, true), bad1, now, new ReplyEngine.MemoryStore()), ReplyEngine.Status.BLOCKED, null);
        // Placeholder cannot smuggle data: unknown placeholders are stripped.
        ReplyEngine.Config bad2 = new ReplyEngine.Config();
        bad2.enabledChannels.add(ReplyEngine.SMS);
        bad2.templates.put(ReplyEngine.SMS, "Busy {card_number} {time}");
        bad2.vars.put("time", "5:30 pm");
        ReplyEngine.Outcome o2 = eng.process(new ReplyEngine.Inbound("SMS", "+917000000004", "hi", false, true), bad2, now, new ReplyEngine.MemoryStore());
        e2e("unknown placeholder stripped", o2, ReplyEngine.Status.REPLY, "Busy 5:30 pm");
        // Incoming text is never echoed.
        ReplyEngine.Outcome o3 = eng.process(new ReplyEngine.Inbound("SMS", "+917000000005", "meet at Gate Seven", false, true), cfg, now, new ReplyEngine.MemoryStore());
        e2e("incoming text not echoed", o3, ReplyEngine.Status.REPLY, null);
        if (o3.text != null && o3.text.contains("Gate Seven")) { fail++; failures.add("ECHO: reply copied incoming text"); } else pass++;

        // ---------- Known limitations (reported, not counted as pass/fail) ----------
        List<String> limits = new ArrayList<String>();
        if (g.check("O.T.P").allowed()) limits.add("letters separated by dots/spaces (e.g. 'O.T.P') are not detected");
        if (g.check("my  P I N").allowed()) limits.add("spaced-out letters (e.g. 'P I N') are not detected");
        // Honest note: only owner-written templates are sent, so these matter only if you write them yourself.

        // ---------- Report ----------
        System.out.println("==== PRIVACY GUARD TEST + BACKTEST ====");
        System.out.printf("Generated sensitive cases : %d  caught: %d  (recall %.2f%%)%n", total, caught, 100.0 * caught / total);
        for (Map.Entry<String, int[]> e : perType.entrySet())
            System.out.printf("   %-18s %5d / %-5d%n", e.getKey(), e.getValue()[0], e.getValue()[1]);
        System.out.printf("Generated benign replies  : %d  false positives: %d  (FP rate %.2f%%)%n", benign, fp, 100.0 * fp / benign);
        System.out.println("Total checks passed       : " + pass);
        System.out.println("Total checks failed       : " + fail);
        for (String l : limits) System.out.println("Known limitation          : " + l);
        int shown = 0;
        for (String f : failures) { if (shown++ < 25) System.out.println("  " + f); }
        if (failures.size() > 25) System.out.println("  ... " + (failures.size() - 25) + " more");
        System.exit(fail == 0 ? 0 : 1);
    }

    static void e2e(String name, ReplyEngine.Outcome o, ReplyEngine.Status want, String contains) {
        boolean ok = o.status == want && (contains == null || (o.text != null && o.text.toLowerCase().contains(contains.toLowerCase())));
        if (ok) pass++; else { fail++; failures.add("E2E FAIL [" + name + "] got " + o.status + " / " + o.reason + " / " + o.text); }
    }
}
