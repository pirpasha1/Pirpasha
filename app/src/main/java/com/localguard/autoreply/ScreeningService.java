package com.localguard.autoreply;

import android.net.Uri;
import android.os.Build;
import android.telecom.Call;
import android.telecom.CallScreeningService;

/** Rejects incoming calls from numbers on your local block list. Needs the "Caller ID & spam app" role. */
public class ScreeningService extends CallScreeningService {
    @Override
    public void onScreenCall(Call.Details details) {
        CallResponse.Builder b = new CallResponse.Builder();
        try {
            boolean incoming = true;
            if (Build.VERSION.SDK_INT >= 29) incoming = details.getCallDirection() == Call.Details.DIRECTION_INCOMING;
            Uri h = details.getHandle();
            String num = h == null ? null : h.getSchemeSpecificPart();
            if (incoming && num != null && Db.get(this).isBlocked(num)) {
                b.setDisallowCall(true).setRejectCall(true).setSkipNotification(true);
                Db.get(this).addLog("CALL", num, "BLOCKED_CALL", "number on your block list");
            }
        } catch (Exception ignored) { }
        respondToCall(details, b.build());
    }
}
