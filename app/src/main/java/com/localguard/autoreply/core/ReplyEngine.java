package com.localguard.autoreply.core;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Decides WHETHER to reply and WHAT to reply. Replies are built only from the owner's own templates;
 * the incoming message text is never copied into the reply. Every reply still passes PrivacyGuard.
 */
public final class ReplyEngine {

    public static final String SMS = "SMS", CALL = "CALL", WHATSAPP = "WHATSAPP";
    public static final String T_URGENT = "URGENT";

    public static final class Inbound {
        public final String channel, sender, body;
        public final boolean group, knownContact;
        public Inbound(String channel, String sender, String body, boolean group, boolean knownContact) {
            this.channel = channel; this.sender = sender; this.body = body;
            this.group = group; this.knownContact = knownContact;
        }
    }

    public static final class Config {
        public Set<String> enabledChannels = new HashSet<String>();
        public boolean contactsOnly = false;
        public long cooldownMs = 30L * 60L * 1000L;
        public Set<String> blocklist = new HashSet<String>();
        /** Keys: SMS, CALL, WHATSAPP, URGENT. */
        public Map<String, String> templates = new HashMap<String, String>();
        /** Whitelisted placeholders, e.g. {time}, {date}. Unknown placeholders are stripped. */
        public Map<String, String> vars = new HashMap<String, String>();
    }

    public interface CooldownStore {
        long last(String key);
        void mark(String key, long time);
    }

    public enum Status { REPLY, SKIP, BLOCKED }

    public static final class Outcome {
        public final Status status; public final String text, reason;
        Outcome(Status s, String t, String r) { status = s; text = t; reason = r; }
    }

    private static final Pattern INBOUND_RISK = Pattern.compile(
        "\\b(?:otp|one[- ]time|verification code|verify|cvv|pin|password|login|log in|debited|credited|a/c|acct|"
        + "upi|txn|transaction|kyc|blocked|suspended|refund|lottery|winner|prize|click|http|www\\.|bit\\.ly)\\b",
        Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);
    private static final Pattern LONG_DIGITS = Pattern.compile("\\d(?:[ \\-.]?\\d){5,}");
    private static final Pattern URGENT = Pattern.compile(
        "\\b(?:urgent|emergency|asap|immediately)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern PLACEHOLDER = Pattern.compile("\\{([a-z_]+)\\}");
    private static final Pattern PHONE_LIKE = Pattern.compile("^\\+?[0-9\\s\\-()]+$");

    private final PrivacyGuard guard;

    public ReplyEngine(PrivacyGuard guard) { this.guard = guard; }

    public static String last10(String s) {
        String d = PrivacyGuard.normalize(s).replaceAll("[^0-9]", "");
        return d.length() > 10 ? d.substring(d.length() - 10) : d;
    }

    public static boolean isPhoneNumber(String sender) {
        if (sender == null) return false;
        String n = PrivacyGuard.normalize(sender).trim();
        if (!PHONE_LIKE.matcher(n).matches()) return false;
        int digits = n.replaceAll("[^0-9]", "").length();
        return digits >= 10 && digits <= 15;
    }

    public Outcome process(Inbound m, Config c, long now, CooldownStore store) {
        if (!c.enabledChannels.contains(m.channel)) return skip("channel disabled");
        if (m.group) return skip("group chat");
        String sender = m.sender == null ? "" : m.sender.trim();
        if (sender.length() == 0) return skip("unknown sender");
        boolean phoneChannel = !WHATSAPP.equals(m.channel);
        if (phoneChannel && !isPhoneNumber(sender)) return skip("service or short-code sender");
        if (phoneChannel && c.blocklist.contains(last10(sender))) return skip("sender blocked");
        if (c.contactsOnly && !m.knownContact) return skip("not in contacts");
        if (m.body != null) {
            String b = PrivacyGuard.normalize(m.body);
            if (INBOUND_RISK.matcher(b).find() || LONG_DIGITS.matcher(b).find()) {
                return skip("incoming message looks like OTP, bank or suspicious link");
            }
        }
        String key = m.channel + ":" + (phoneChannel ? last10(sender) : sender.toLowerCase(Locale.ROOT));
        long last = store.last(key);
        if (last > 0 && now - last < c.cooldownMs) return skip("cooldown");

        String tpl = null;
        if (m.body != null && URGENT.matcher(m.body).find()) tpl = c.templates.get(T_URGENT);
        if (tpl == null || tpl.trim().length() == 0) tpl = c.templates.get(m.channel);
        if (tpl == null || tpl.trim().length() == 0) return skip("no template");

        String text = render(tpl, c.vars);
        PrivacyGuard.Verdict v = guard.check(text);
        if (!v.allowed()) return new Outcome(Status.BLOCKED, null, "privacy guard: " + v.summary());
        store.mark(key, now);
        return new Outcome(Status.REPLY, text, "ok");
    }

    public static String render(String tpl, Map<String, String> vars) {
        java.util.regex.Matcher m = PLACEHOLDER.matcher(tpl);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            String v = vars.get(m.group(1));
            m.appendReplacement(sb, java.util.regex.Matcher.quoteReplacement(v == null ? "" : v));
        }
        m.appendTail(sb);
        return sb.toString().replaceAll("\\s{2,}", " ").trim();
    }

    private static Outcome skip(String why) { return new Outcome(Status.SKIP, null, why); }

    /** Simple in-memory store, used by tests and as a fallback. */
    public static final class MemoryStore implements CooldownStore {
        private final Map<String, Long> map = Collections.synchronizedMap(new HashMap<String, Long>());
        public long last(String key) { Long v = map.get(key); return v == null ? 0L : v; }
        public void mark(String key, long time) { map.put(key, time); }
    }
}
