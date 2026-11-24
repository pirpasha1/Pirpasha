package com.localguard.autoreply;

import android.app.Notification;
import android.app.PendingIntent;
import android.app.RemoteInput;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import com.localguard.autoreply.core.ReplyEngine;

/**
 * Replies to WhatsApp / WhatsApp Business through the notification's own "Reply" action.
 * Needs Notification Access. No WhatsApp login, no server, no internet: it only taps the same Reply
 * button you would tap yourself. Group chats are skipped.
 */
public class WhatsAppListener extends NotificationListenerService {

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        try { handle(sbn); } catch (Throwable ignored) { }
    }

    private void handle(StatusBarNotification sbn) throws Exception {
        String pkg = sbn.getPackageName();
        if (!"com.whatsapp".equals(pkg) && !"com.whatsapp.w4b".equals(pkg)) return;
        Notification n = sbn.getNotification();
        if (n == null || (n.flags & Notification.FLAG_GROUP_SUMMARY) != 0) return;

        Bundle ex = n.extras;
        if (ex == null) return;
        boolean group = ex.getBoolean("android.isGroupConversation", false)
                || ex.getCharSequence("android.conversationTitle") != null;
        CharSequence title = ex.getCharSequence(Notification.EXTRA_TITLE);
        CharSequence text = ex.getCharSequence(Notification.EXTRA_TEXT);
        if (title == null || "WhatsApp".contentEquals(title)) return;

        final Notification.Action reply = findReplyAction(n);
        if (reply == null) return;

        final Context ctx = getApplicationContext();
        ReplyEngine.Inbound in = new ReplyEngine.Inbound(
            ReplyEngine.WHATSAPP, title.toString(), text == null ? null : text.toString(), group, false);
        Replier.handle(ctx, in, new Replier.Send() {
            public boolean send(String reply_text) { return sendReply(ctx, reply, reply_text); }
        });
    }

    private static Notification.Action findReplyAction(Notification n) {
        if (n.actions != null) {
            for (Notification.Action a : n.actions) if (hasRemoteInput(a)) return a;
        }
        Notification.WearableExtender w = new Notification.WearableExtender(n);
        for (Notification.Action a : w.getActions()) if (hasRemoteInput(a)) return a;
        return null;
    }

    private static boolean hasRemoteInput(Notification.Action a) {
        return a != null && a.getRemoteInputs() != null && a.getRemoteInputs().length > 0 && a.actionIntent != null;
    }

    private static boolean sendReply(Context ctx, Notification.Action a, String text) {
        try {
            RemoteInput[] inputs = a.getRemoteInputs();
            Intent fill = new Intent();
            Bundle results = new Bundle();
            for (RemoteInput ri : inputs) results.putCharSequence(ri.getResultKey(), text);
            RemoteInput.addResultsToIntent(inputs, fill, results);
            a.actionIntent.send(ctx, 0, fill);
            return true;
        } catch (PendingIntent.CanceledException e) {
            return false;
        }
    }
}
