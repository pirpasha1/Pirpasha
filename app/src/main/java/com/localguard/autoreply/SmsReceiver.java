package com.localguard.autoreply;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.provider.Telephony;
import android.telephony.SmsMessage;

import com.localguard.autoreply.core.ReplyEngine;

/** Incoming SMS -> optional auto-reply SMS. The incoming text is only inspected, never stored or echoed. */
public class SmsReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(final Context ctx, Intent intent) {
        if (intent == null || !Telephony.Sms.Intents.SMS_RECEIVED_ACTION.equals(intent.getAction())) return;
        SmsMessage[] msgs = Telephony.Sms.Intents.getMessagesFromIntent(intent);
        if (msgs == null || msgs.length == 0 || msgs[0] == null) return;
        final String sender = msgs[0].getOriginatingAddress();
        StringBuilder body = new StringBuilder();
        for (SmsMessage m : msgs) if (m != null && m.getMessageBody() != null) body.append(m.getMessageBody());

        ReplyEngine.Inbound in = new ReplyEngine.Inbound(
            ReplyEngine.SMS, sender, body.toString(), false, Replier.isContact(ctx, sender));
        Replier.handle(ctx, in, new Replier.Send() {
            public boolean send(String text) { return Replier.sendSms(ctx, sender, text); }
        });
    }
}
