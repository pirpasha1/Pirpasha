package com.localguard.autoreply;

import android.Manifest;
import android.app.Activity;
import android.app.role.RoleManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Typeface;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import com.localguard.autoreply.core.PrivacyGuard;
import com.localguard.autoreply.core.ReplyEngine;

import java.io.File;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Single-screen settings UI, built in code (no XML, no libraries). */
public class MainActivity extends Activity {
    private Switch swSms, swCall, swWa, swRec, swContacts;
    private EditText etCooldown, etBack, etSms, etCallTpl, etWa, etUrgent, etAllowed, etTest, etBlock;
    private TextView tvTestResult, tvLog, tvRecs;
    private LinearLayout root;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        setTitle("CallGuard Local");
        ScrollView sv = new ScrollView(this);
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(12), dp(16), dp(32));
        sv.addView(root);
        setContentView(sv);

        SharedPreferences p = Prefs.sp(this);

        head("100% on this phone");
        note("This app has no internet permission, so nothing can be uploaded. Messages are never stored; "
           + "only a short activity log, your settings and recordings stay in this app's private storage.");

        head("1. Turn things on");
        swSms = sw("Auto-reply to SMS", p.getBoolean("sms_on", false));
        swCall = sw("Auto-reply (SMS) after a missed call", p.getBoolean("call_on", false));
        swWa = sw("Auto-reply on WhatsApp (1-to-1 chats only)", p.getBoolean("wa_on", false));
        swContacts = sw("Reply only to people in my contacts", p.getBoolean("contacts_only", false));
        swRec = sw("Record calls (best effort, see note)", p.getBoolean("rec_on", false));
        note("SMS replies may cost carrier SMS charges. Recording: tell the other person; laws on recording differ. "
           + "Android 10+ blocks the other side's voice unless speakerphone is on.");

        head("2. Permissions & access");
        btn("Grant permissions (SMS, calls, contacts, mic)", new View.OnClickListener() {
            public void onClick(View v) { askPermissions(); }
        });
        btn("Allow WhatsApp reading (Notification access)", new View.OnClickListener() {
            public void onClick(View v) { startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)); }
        });
        btn("Enable call blocking (Caller ID & spam role)", new View.OnClickListener() {
            public void onClick(View v) { askScreeningRole(); }
        });

        head("3. Your replies (templates)");
        note("Replies are built ONLY from these texts. Placeholders: {time} {date} {back}. "
           + "The incoming message is never copied into a reply.");
        etCooldown = edit("Minutes before replying to the same person again", String.valueOf(p.getInt("cooldown_min", 30)), false);
        etCooldown.setInputType(InputType.TYPE_CLASS_NUMBER);
        etBack = edit("{back} text, e.g. 'after 6 pm'", Prefs.s(this, "back_at", "later today"), false);
        label("SMS reply"); etSms = edit("", Prefs.s(this, "tpl_sms", Prefs.DEF_SMS), true);
        label("Missed-call reply"); etCallTpl = edit("", Prefs.s(this, "tpl_call", Prefs.DEF_CALL), true);
        label("WhatsApp reply"); etWa = edit("", Prefs.s(this, "tpl_wa", Prefs.DEF_WA), true);
        label("Reply when the message says 'urgent'"); etUrgent = edit("", Prefs.s(this, "tpl_urgent", Prefs.DEF_URGENT), true);

        head("4. Privacy allow-list");
        note("Everything sensitive is blocked by default: card, Aadhaar, PAN, IFSC, bank account, UPI ID, e-mail, phone "
           + "numbers, OTP/PIN/password words, amounts, addresses, links. If you WANT a reply to contain one specific "
           + "detail (for example an office e-mail), type it here exactly, one per line (min 4 characters).");
        etAllowed = edit("", Prefs.s(this, "allowed", ""), true);

        btn("SAVE SETTINGS", new View.OnClickListener() {
            public void onClick(View v) { save(); }
        });

        head("5. Test the privacy guard");
        etTest = edit("Type a reply to test", "", true);
        btn("Check", new View.OnClickListener() {
            public void onClick(View v) {
                PrivacyGuard.Verdict vd = Prefs.guard(MainActivity.this).check(etTest.getText().toString());
                tvTestResult.setText(vd.allowed() ? "OK: this text would be sent." : "BLOCKED: " + vd.summary());
            }
        });
        tvTestResult = note("");

        head("6. Blocked callers");
        etBlock = edit("Phone number to block", "", false);
        etBlock.setInputType(InputType.TYPE_CLASS_PHONE);
        btn("Block number", new View.OnClickListener() {
            public void onClick(View v) { Db.get(MainActivity.this).addBlock(etBlock.getText().toString()); etBlock.setText(""); refresh(); }
        });
        btn("Unblock number", new View.OnClickListener() {
            public void onClick(View v) { Db.get(MainActivity.this).removeBlock(etBlock.getText().toString()); etBlock.setText(""); refresh(); }
        });

        head("7. Recordings");
        btn("Record now", new View.OnClickListener() {
            public void onClick(View v) { try { RecorderService.start(MainActivity.this); } catch (Exception e) { toast("Could not start recording"); } }
        });
        btn("Stop recording", new View.OnClickListener() {
            public void onClick(View v) { stopService(new Intent(MainActivity.this, RecorderService.class)); refresh(); }
        });
        btn("Delete all recordings", new View.OnClickListener() {
            public void onClick(View v) {
                File[] fs = RecorderService.dir(MainActivity.this).listFiles();
                if (fs != null) for (File f : fs) f.delete();
                refresh();
            }
        });
        tvRecs = note("");

        head("8. Activity log");
        btn("Refresh", new View.OnClickListener() { public void onClick(View v) { refresh(); } });
        btn("Clear log", new View.OnClickListener() {
            public void onClick(View v) { Db.get(MainActivity.this).clearLog(); refresh(); }
        });
        tvLog = note("");
        refresh();
    }

    @Override protected void onResume() { super.onResume(); if (tvLog != null) refresh(); }

    // ---------- actions ----------
    private void save() {
        Context c = this;
        Map<String, String> tpls = new LinkedHashMap<String, String>();
        tpls.put("SMS reply", etSms.getText().toString());
        tpls.put("Missed-call reply", etCallTpl.getText().toString());
        tpls.put("WhatsApp reply", etWa.getText().toString());
        tpls.put("Urgent reply", etUrgent.getText().toString());

        // Validate against the guard using the allow-list as typed now.
        List<String> allowed = new ArrayList<String>();
        for (String line : etAllowed.getText().toString().split("\\r?\\n")) if (line.trim().length() >= 4) allowed.add(line.trim());
        PrivacyGuard g = new PrivacyGuard(allowed);
        java.util.Map<String, String> vars = Prefs.vars(c);
        vars.put("back", etBack.getText().toString());
        for (Map.Entry<String, String> e : tpls.entrySet()) {
            PrivacyGuard.Verdict v = g.check(ReplyEngine.render(e.getValue(), vars));
            if (!v.allowed()) {
                toast("Not saved. '" + e.getKey() + "' contains blocked details: " + v.summary());
                return;
            }
        }
        int cd = 30;
        try { cd = Integer.parseInt(etCooldown.getText().toString().trim()); } catch (Exception ignored) { }
        Prefs.sp(c).edit()
            .putBoolean("sms_on", swSms.isChecked())
            .putBoolean("call_on", swCall.isChecked())
            .putBoolean("wa_on", swWa.isChecked())
            .putBoolean("rec_on", swRec.isChecked())
            .putBoolean("contacts_only", swContacts.isChecked())
            .putInt("cooldown_min", Math.max(1, cd))
            .putString("back_at", etBack.getText().toString())
            .putString("tpl_sms", etSms.getText().toString())
            .putString("tpl_call", etCallTpl.getText().toString())
            .putString("tpl_wa", etWa.getText().toString())
            .putString("tpl_urgent", etUrgent.getText().toString())
            .putString("allowed", etAllowed.getText().toString())
            .apply();
        toast("Saved");
    }

    private void askPermissions() {
        List<String> perms = new ArrayList<String>();
        perms.add(Manifest.permission.RECEIVE_SMS);
        perms.add(Manifest.permission.SEND_SMS);
        perms.add(Manifest.permission.READ_PHONE_STATE);
        perms.add(Manifest.permission.READ_CALL_LOG);
        perms.add(Manifest.permission.READ_CONTACTS);
        perms.add(Manifest.permission.RECORD_AUDIO);
        if (Build.VERSION.SDK_INT >= 33) perms.add(Manifest.permission.POST_NOTIFICATIONS);
        requestPermissions(perms.toArray(new String[0]), 1);
    }

    private void askScreeningRole() {
        if (Build.VERSION.SDK_INT >= 29) {
            try {
                RoleManager rm = (RoleManager) getSystemService(Context.ROLE_SERVICE);
                startActivityForResult(rm.createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING), 2);
            } catch (Exception e) { toast("Not available on this phone"); }
        } else {
            toast("Needs Android 10 or newer");
        }
    }

    private void refresh() {
        List<String> logs = Db.get(this).recent(40);
        StringBuilder sb = new StringBuilder();
        for (String l : logs) sb.append(l).append("\n");
        tvLog.setText(logs.isEmpty() ? "Nothing yet." : sb.toString());

        StringBuilder rs = new StringBuilder();
        File[] fs = RecorderService.dir(this).listFiles();
        if (fs != null) for (File f : fs) rs.append(f.getName()).append("  (").append(f.length() / 1024).append(" KB)\n");
        tvRecs.setText(rs.length() == 0 ? "No recordings. Folder: Android/data/com.localguard.autoreply/files/recordings"
                                         : rs + "Folder: Android/data/com.localguard.autoreply/files/recordings");
    }

    // ---------- tiny UI helpers ----------
    private int dp(int v) { return (int) (v * getResources().getDisplayMetrics().density); }
    private void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_LONG).show(); }

    private TextView head(String s) {
        TextView t = new TextView(this);
        t.setText(s); t.setTextSize(18); t.setTypeface(Typeface.DEFAULT_BOLD);
        t.setPadding(0, dp(18), 0, dp(4));
        root.addView(t);
        return t;
    }
    private TextView label(String s) { TextView t = new TextView(this); t.setText(s); t.setPadding(0, dp(8), 0, 0); root.addView(t); return t; }
    private TextView note(String s) { TextView t = new TextView(this); t.setText(s); t.setTextSize(13); t.setPadding(0, dp(2), 0, dp(6)); root.addView(t); return t; }
    private Switch sw(String s, boolean on) { Switch w = new Switch(this); w.setText(s); w.setChecked(on); w.setPadding(0, dp(6), 0, dp(6)); root.addView(w); return w; }
    private EditText edit(String hint, String value, boolean multi) {
        EditText e = new EditText(this);
        e.setHint(hint); e.setText(value);
        if (multi) { e.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE); e.setMinLines(2); }
        root.addView(e);
        return e;
    }
    private Button btn(String s, View.OnClickListener l) { Button b = new Button(this); b.setText(s); b.setOnClickListener(l); root.addView(b); return b; }
}
