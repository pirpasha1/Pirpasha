package com.localguard.autoreply;

import android.content.Context;
import android.content.SharedPreferences;

import com.localguard.autoreply.core.PrivacyGuard;
import com.localguard.autoreply.core.ReplyEngine;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** All settings live in app-private SharedPreferences on this phone only. */
public final class Prefs {
    private Prefs() {}

    public static final String DEF_SMS = "Hi, I'm unable to reply right now. I'll get back to you as soon as I can.";
    public static final String DEF_CALL = "Sorry I missed your call. I'll call you back soon.";
    public static final String DEF_WA = "Hi, I'm unavailable right now and will reply when I can.";
    public static final String DEF_URGENT = "Noted as urgent. I'll call you at the first chance.";

    public static SharedPreferences sp(Context c) {
        return c.getApplicationContext().getSharedPreferences("cg", Context.MODE_PRIVATE);
    }

    public static boolean b(Context c, String k, boolean d) { return sp(c).getBoolean(k, d); }
    public static String s(Context c, String k, String d) { return sp(c).getString(k, d); }

    public static List<String> allowedLiterals(Context c) {
        List<String> out = new ArrayList<String>();
        for (String line : s(c, "allowed", "").split("\\r?\\n")) {
            String t = line.trim();
            if (t.length() >= 4) out.add(t);
        }
        return out;
    }

    public static PrivacyGuard guard(Context c) { return new PrivacyGuard(allowedLiterals(c)); }

    public static Map<String, String> vars(Context c) {
        Map<String, String> v = new HashMap<String, String>();
        Date now = new Date();
        v.put("time", new SimpleDateFormat("h:mm a", Locale.ENGLISH).format(now));
        v.put("date", new SimpleDateFormat("dd-MM-yyyy", Locale.ENGLISH).format(now));
        v.put("back", s(c, "back_at", "later today"));
        return v;
    }

    public static Map<String, String> templates(Context c) {
        Map<String, String> t = new HashMap<String, String>();
        t.put(ReplyEngine.SMS, s(c, "tpl_sms", DEF_SMS));
        t.put(ReplyEngine.CALL, s(c, "tpl_call", DEF_CALL));
        t.put(ReplyEngine.WHATSAPP, s(c, "tpl_wa", DEF_WA));
        t.put(ReplyEngine.T_URGENT, s(c, "tpl_urgent", DEF_URGENT));
        return t;
    }

    public static ReplyEngine.Config config(Context c) {
        ReplyEngine.Config cfg = new ReplyEngine.Config();
        if (b(c, "sms_on", false)) cfg.enabledChannels.add(ReplyEngine.SMS);
        if (b(c, "call_on", false)) cfg.enabledChannels.add(ReplyEngine.CALL);
        if (b(c, "wa_on", false)) cfg.enabledChannels.add(ReplyEngine.WHATSAPP);
        cfg.contactsOnly = b(c, "contacts_only", false);
        cfg.cooldownMs = Math.max(1, sp(c).getInt("cooldown_min", 30)) * 60000L;
        cfg.blocklist = Db.get(c).blocklist();
        cfg.templates = templates(c);
        cfg.vars = vars(c);
        return cfg;
    }
}
