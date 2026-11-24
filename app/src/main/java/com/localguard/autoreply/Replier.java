package com.localguard.autoreply;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.provider.ContactsContract;
import android.telephony.SmsManager;

import com.localguard.autoreply.core.ReplyEngine;

import java.util.ArrayList;

/** Glue: run the engine (policy + privacy guard), log the outcome, and only then send. */
public final class Replier {
    private Replier() {}

    public interface Send { boolean send(String text); }

    public static void handle(Context ctx, ReplyEngine.Inbound in, Send send) {
        Context app = ctx.getApplicationContext();
        Db db = Db.get(app);
        ReplyEngine.Outcome o;
        try {
            o = new ReplyEngine(Prefs.guard(app)).process(in, Prefs.config(app), System.currentTimeMillis(), db);
        } catch (Exception e) {
            db.addLog(in.channel, in.sender, "ERROR", e.getClass().getSimpleName());
            return;
        }
        if (o.status == ReplyEngine.Status.REPLY) {
            boolean ok = false;
            try { ok = send.send(o.text); } catch (Exception ignored) { }
            db.addLog(in.channel, in.sender, ok ? "REPLIED" : "SEND_FAILED", ok ? "" : "could not send");
        } else {
            db.addLog(in.channel, in.sender, o.status.name(), o.reason);
        }
    }

    public static boolean sendSms(Context c, String number, String text) {
        try {
            SmsManager sm = Build.VERSION.SDK_INT >= 31
                ? c.getSystemService(SmsManager.class) : SmsManager.getDefault();
            ArrayList<String> parts = sm.divideMessage(text);
            sm.sendMultipartTextMessage(number, null, parts, null, null);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public static boolean isContact(Context c, String number) {
        if (number == null || c.checkSelfPermission(Manifest.permission.READ_CONTACTS) != PackageManager.PERMISSION_GRANTED) return false;
        Cursor cur = null;
        try {
            Uri u = Uri.withAppendedPath(ContactsContract.PhoneLookup.CONTENT_FILTER_URI, Uri.encode(number));
            cur = c.getContentResolver().query(u, new String[]{ContactsContract.PhoneLookup._ID}, null, null, null);
            return cur != null && cur.moveToFirst();
        } catch (Exception e) {
            return false;
        } finally {
            if (cur != null) cur.close();
        }
    }
}
