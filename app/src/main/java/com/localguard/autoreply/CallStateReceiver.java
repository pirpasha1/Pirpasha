package com.localguard.autoreply;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.telephony.TelephonyManager;

import com.localguard.autoreply.core.ReplyEngine;

/**
 * Watches call state: sends the missed-call SMS reply, and starts/stops the (best-effort) call recorder.
 * The caller's number only arrives if READ_CALL_LOG + READ_PHONE_STATE are granted.
 */
public class CallStateReceiver extends BroadcastReceiver {
    private static boolean ringing = false;
    private static boolean answered = false;
    private static String number = null;

    @Override
    public synchronized void onReceive(final Context ctx, Intent intent) {
        if (intent == null || !TelephonyManager.ACTION_PHONE_STATE_CHANGED.equals(intent.getAction())) return;
        String state = intent.getStringExtra(TelephonyManager.EXTRA_STATE);
        String num = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER);
        if (state == null) return;

        if (TelephonyManager.EXTRA_STATE_RINGING.equals(state)) {
            if (!ringing) { ringing = true; answered = false; number = null; }
            if (num != null && num.length() > 0) number = num;

        } else if (TelephonyManager.EXTRA_STATE_OFFHOOK.equals(state)) {
            if (ringing) answered = true;
            if (Prefs.b(ctx, "rec_on", false)) {
                try {
                    RecorderService.start(ctx);
                } catch (Exception e) {
                    // Android 12+ often blocks starting a microphone service from the background.
                    Db.get(ctx).addLog("RECORD", "", "RECORD_FAILED", "Android blocked background recording start");
                }
            }

        } else if (TelephonyManager.EXTRA_STATE_IDLE.equals(state)) {
            try { ctx.stopService(new Intent(ctx, RecorderService.class)); } catch (Exception ignored) { }
            if (ringing && !answered) {
                final String n = number;
                if (n == null) {
                    Db.get(ctx).addLog(ReplyEngine.CALL, "", "SKIP", "number hidden or call-log permission missing");
                } else {
                    ReplyEngine.Inbound in = new ReplyEngine.Inbound(
                        ReplyEngine.CALL, n, null, false, Replier.isContact(ctx, n));
                    Replier.handle(ctx, in, new Replier.Send() {
                        public boolean send(String text) { return Replier.sendSms(ctx, n, text); }
                    });
                }
            }
            ringing = false; answered = false; number = null;
        }
    }
}
