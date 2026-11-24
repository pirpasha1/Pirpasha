package com.localguard.autoreply.core;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Last line of defence before ANY outgoing auto-reply is sent.
 *
 * Default is deny: financial, credential, ID and personal details are blocked.
 * The only way through is an exact literal the owner put on the allow-list
 * (for example a business e-mail or office number). Pure Java so it is unit-tested on a plain JVM.
 */
public final class PrivacyGuard {

    public enum Category {
        CARD_NUMBER, AADHAAR, PAN, IFSC, GSTIN, PASSPORT, UPI_ID, EMAIL, PHONE_NUMBER,
        LONG_NUMBER, CODE_NUMBER, CREDENTIAL_WORD, ID_DOCUMENT_WORD, FINANCIAL_WORD,
        FINANCIAL_AMOUNT, ADDRESS_OR_PERSONAL, LINK, SPELLED_DIGITS
    }

    public static final class Finding {
        public final Category category;
        public final int position;
        Finding(Category c, int p) { category = c; position = p; }
    }

    /** Result of a check. Never contains the offending text, only categories. */
    public static final class Verdict {
        public final List<Finding> findings;
        Verdict(List<Finding> f) { findings = Collections.unmodifiableList(f); }
        public boolean allowed() { return findings.isEmpty(); }
        public String summary() {
            Set<String> names = new LinkedHashSet<String>();
            for (Finding f : findings) names.add(f.category.name());
            StringBuilder sb = new StringBuilder();
            for (String n : names) { if (sb.length() > 0) sb.append(','); sb.append(n); }
            return sb.toString();
        }
    }

    private static final int CI = Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE;

    private static final class Rule {
        final Category category; final Pattern pattern;
        Rule(Category c, String regex) { category = c; pattern = Pattern.compile(regex, CI); }
    }

    private static final Rule[] RULES = new Rule[] {
        new Rule(Category.PAN, "\\b[A-Z]{5}\\d{4}[A-Z]\\b"),
        new Rule(Category.IFSC, "\\b[A-Z]{4}0[A-Z0-9]{6}\\b"),
        new Rule(Category.GSTIN, "\\b\\d{2}[A-Z]{5}\\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\\b"),
        new Rule(Category.PASSPORT, "\\b[A-PR-WY][1-9]\\d{6}\\b"),
        new Rule(Category.EMAIL, "[A-Z0-9._%+\\-]+@[A-Z0-9\\-]+(?:\\.[A-Z0-9\\-]+)+"),
        new Rule(Category.UPI_ID, "[A-Z0-9._\\-]{2,}@[A-Z][A-Z0-9]{1,}(?![A-Z0-9\\-]|\\.[A-Z0-9])"),
        new Rule(Category.LINK, "(?:https?://|www\\.)\\S+|\\b[A-Z0-9\\-]+\\.(?:com|in|net|org|xyz|top|ly|me|io|app|info|biz|co\\.in)\\b(?:/\\S*)?"),
        new Rule(Category.CREDENTIAL_WORD,
            "\\b(?:otp|cvv|cvc|mpin|pin|passcode|password|passwd|pwd|security code|verification code|"
            + "secret key|api key|apikey|access token|auth token|login id|username|user id|userid|credentials?)\\b"),
        new Rule(Category.ID_DOCUMENT_WORD,
            "\\b(?:aadhaar|aadhar|adhar|pan card|passport|voter id|driving licen[cs]e|ifsc|gstin|ssn)\\b"),
        new Rule(Category.FINANCIAL_WORD,
            "\\b(?:salary|income|balance|net worth|loan|emi|savings|investment|portfolio|mutual fund|folio|"
            + "bank account|account (?:no|number)|a/c|credit card|debit card|card (?:no|number)|net ?banking|"
            + "upi|neft|rtgs|imps|cheque|demat)\\b"),
        new Rule(Category.FINANCIAL_AMOUNT,
            "(?:₹|\\brs\\.?|\\binr\\b|\\busd\\b|\\$|€|£)\\s*\\d"
            + "|\\d[\\d,.]*\\s*(?:rs\\b|rupees|lakhs?|lacs?|crores?|dollars|inr\\b|usd\\b)"),
        new Rule(Category.ADDRESS_OR_PERSONAL,
            "\\b(?:address|flat no|house no|plot no|survey no|door no|pin ?code|zip ?code|dob|d\\.o\\.b|"
            + "date of birth|born on|home location|live location|my location|residence|whereabouts)\\b"
            + "|\\bi (?:live|stay|reside) (?:at|in)\\b"),
        new Rule(Category.SPELLED_DIGITS,
            "\\b(?:(?:zero|one|two|three|four|five|six|seven|eight|nine)[\\s\\-,.]+){7,}")
    };

    // Dates and clock times are common in replies and are not sensitive; mask them before digit-run analysis.
    private static final Pattern DATE_DMY = Pattern.compile(
        "\\b(?:0?[1-9]|[12]\\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.](?:\\d{4}|\\d{2})\\b");
    private static final Pattern DATE_ISO = Pattern.compile(
        "\\b\\d{4}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\\d|3[01])\\b");
    private static final Pattern TIME = Pattern.compile("\\b\\d{1,2}:\\d{2}(?::\\d{2})?\\b");
    private static final Pattern DIGIT_RUN = Pattern.compile("\\d(?:[ \\-.]{0,2}\\d)*");

    private final List<String> allowed = new ArrayList<String>();

    /** @param allowedLiterals exact strings the owner explicitly permits (minimum 4 characters each). */
    public PrivacyGuard(Collection<String> allowedLiterals) {
        if (allowedLiterals != null) {
            for (String s : allowedLiterals) {
                if (s == null) continue;
                String n = normalize(s).trim();
                if (n.length() >= 4) allowed.add(n);
            }
        }
        Collections.sort(allowed, new Comparator<String>() {
            public int compare(String a, String b) { return b.length() - a.length(); }
        });
    }

    /** NFKC, ASCII-fies every Unicode digit (Devanagari, Gujarati, full-width...) and drops zero-width characters. */
    public static String normalize(String s) {
        if (s == null) return "";
        String n = Normalizer.normalize(s, Normalizer.Form.NFKC);
        StringBuilder sb = new StringBuilder(n.length());
        int i = 0;
        while (i < n.length()) {
            int cp = n.codePointAt(i);
            i += Character.charCount(cp);
            if (cp == 0x200B || cp == 0x200C || cp == 0x200D || cp == 0x2060 || cp == 0xFEFF || cp == 0x00AD) continue;
            if (Character.isDigit(cp)) { sb.append((char) ('0' + Character.digit(cp, 10))); continue; }
            sb.appendCodePoint(cp);
        }
        return sb.toString();
    }

    public Verdict check(String text) {
        String t = normalize(text);
        for (String a : allowed) {
            t = Pattern.compile(Pattern.quote(a), CI).matcher(t).replaceAll("\u0001");
        }
        List<Finding> found = new ArrayList<Finding>();
        for (Rule r : RULES) {
            Matcher m = r.pattern.matcher(t);
            while (m.find()) found.add(new Finding(r.category, m.start()));
        }
        scanDigits(t, found);
        return new Verdict(found);
    }

    private static String mask(String t, Pattern p) {
        Matcher m = p.matcher(t);
        StringBuilder sb = new StringBuilder(t);
        while (m.find()) for (int i = m.start(); i < m.end(); i++) sb.setCharAt(i, '#');
        return sb.toString();
    }

    private static void scanDigits(String t, List<Finding> out) {
        String masked = mask(mask(mask(t, DATE_ISO), DATE_DMY), TIME);
        Matcher m = DIGIT_RUN.matcher(masked);
        while (m.find()) {
            String d = m.group().replaceAll("[^0-9]", "");
            int n = d.length();
            Category c = null;
            if (n >= 13 && n <= 19 && Validators.luhn(d)) c = Category.CARD_NUMBER;
            else if (n == 12 && d.charAt(0) >= '2' && Validators.verhoeff(d)) c = Category.AADHAAR;
            else if ((n == 10 && d.charAt(0) >= '6')
                  || (n == 11 && d.charAt(0) == '0' && d.charAt(1) >= '6')
                  || (n == 12 && d.startsWith("91") && d.charAt(2) >= '6')
                  || (n == 13 && d.startsWith("091") && d.charAt(3) >= '6')) c = Category.PHONE_NUMBER;
            else if (n >= 9) c = Category.LONG_NUMBER;
            else if (n >= 6) c = Category.CODE_NUMBER;
            if (c != null) out.add(new Finding(c, m.start()));
        }
    }
}
