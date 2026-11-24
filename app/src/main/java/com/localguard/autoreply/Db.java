package com.localguard.autoreply;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import com.localguard.autoreply.core.ReplyEngine;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Local SQLite database (app-private storage). Holds the activity log, the block list and reply cool-downs.
 * Message bodies are NEVER stored.
 */
public final class Db extends SQLiteOpenHelper implements ReplyEngine.CooldownStore {
    private static Db inst;

    public static synchronized Db get(Context c) {
        if (inst == null) inst = new Db(c.getApplicationContext());
        return inst;
    }

    private Db(Context c) { super(c, "cg.db", null, 1); }

    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, channel TEXT, sender TEXT, status TEXT, reason TEXT)");
        db.execSQL("CREATE TABLE blocklist (number TEXT PRIMARY KEY)");
        db.execSQL("CREATE TABLE cooldown (k TEXT PRIMARY KEY, ts INTEGER)");
    }

    @Override public void onUpgrade(SQLiteDatabase db, int o, int n) { }

    // ---- cooldown ----
    @Override public synchronized long last(String key) {
        Cursor c = getReadableDatabase().rawQuery("SELECT ts FROM cooldown WHERE k=?", new String[]{key});
        try { return c.moveToFirst() ? c.getLong(0) : 0L; } finally { c.close(); }
    }

    @Override public synchronized void mark(String key, long t) {
        ContentValues v = new ContentValues();
        v.put("k", key); v.put("ts", t);
        getWritableDatabase().insertWithOnConflict("cooldown", null, v, SQLiteDatabase.CONFLICT_REPLACE);
    }

    // ---- log ----
    public synchronized void addLog(String channel, String sender, String status, String reason) {
        SQLiteDatabase db = getWritableDatabase();
        ContentValues v = new ContentValues();
        v.put("ts", System.currentTimeMillis());
        v.put("channel", channel); v.put("sender", sender == null ? "" : sender);
        v.put("status", status); v.put("reason", reason == null ? "" : reason);
        db.insert("log", null, v);
        db.execSQL("DELETE FROM log WHERE id NOT IN (SELECT id FROM log ORDER BY id DESC LIMIT 500)");
    }

    public synchronized List<String> recent(int n) {
        List<String> out = new ArrayList<String>();
        SimpleDateFormat f = new SimpleDateFormat("dd/MM HH:mm", Locale.ENGLISH);
        Cursor c = getReadableDatabase().rawQuery(
            "SELECT ts, channel, sender, status, reason FROM log ORDER BY id DESC LIMIT " + n, null);
        try {
            while (c.moveToNext()) {
                out.add(f.format(new Date(c.getLong(0))) + "  " + c.getString(1) + "  " + c.getString(2)
                    + "\n    " + c.getString(3) + (c.getString(4).length() > 0 ? " - " + c.getString(4) : ""));
            }
        } finally { c.close(); }
        return out;
    }

    public synchronized void clearLog() { getWritableDatabase().delete("log", null, null); }

    // ---- block list (stored as last 10 digits) ----
    public synchronized Set<String> blocklist() {
        Set<String> s = new HashSet<String>();
        Cursor c = getReadableDatabase().rawQuery("SELECT number FROM blocklist", null);
        try { while (c.moveToNext()) s.add(c.getString(0)); } finally { c.close(); }
        return s;
    }

    public synchronized void addBlock(String number) {
        String n = ReplyEngine.last10(number);
        if (n.length() < 7) return;
        ContentValues v = new ContentValues();
        v.put("number", n);
        getWritableDatabase().insertWithOnConflict("blocklist", null, v, SQLiteDatabase.CONFLICT_IGNORE);
    }

    public synchronized void removeBlock(String number) {
        getWritableDatabase().delete("blocklist", "number=?", new String[]{ReplyEngine.last10(number)});
    }

    public boolean isBlocked(String number) { return blocklist().contains(ReplyEngine.last10(number)); }
}
