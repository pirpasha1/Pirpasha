package com.localguard.autoreply;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.media.MediaRecorder;
import android.os.Build;
import android.os.IBinder;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * Best-effort audio recorder. Files are saved ONLY in this app's private storage on the phone.
 *
 * Honest limits: Android 10+ stops normal apps from capturing the other person's voice in a phone call.
 * With speakerphone on you get both sides; otherwise mostly your own voice. A visible notification is
 * always shown while recording.
 */
public class RecorderService extends Service {
    private static final String CHANNEL = "rec";
    private MediaRecorder recorder;
    private File file;

    public static void start(Context c) {
        Intent i = new Intent(c, RecorderService.class);
        if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i); else c.startService(i);
    }

    public static File dir(Context c) {
        File d = c.getExternalFilesDir("recordings");
        if (d != null && !d.exists()) d.mkdirs();
        return d;
    }

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(new NotificationChannel(CHANNEL, "Recording", NotificationManager.IMPORTANCE_LOW));
        }
        Notification note = new Notification.Builder(this, CHANNEL)
            .setContentTitle("CallGuard Local is recording")
            .setContentText("Saved only on this phone")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .build();
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(41, note, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
        } else {
            startForeground(41, note);
        }

        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            Db.get(this).addLog("RECORD", "", "RECORD_FAILED", "microphone permission missing");
            stopSelf();
            return START_NOT_STICKY;
        }
        if (recorder == null && !beginRecording()) {
            stopSelf();
            return START_NOT_STICKY;
        }
        return START_NOT_STICKY;
    }

    private boolean beginRecording() {
        file = new File(dir(this), "call_" + new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.ENGLISH).format(new Date()) + ".m4a");
        int[] sources = {MediaRecorder.AudioSource.VOICE_RECOGNITION, MediaRecorder.AudioSource.MIC};
        for (int src : sources) {
            try {
                MediaRecorder r = Build.VERSION.SDK_INT >= 31 ? new MediaRecorder(this) : new MediaRecorder();
                r.setAudioSource(src);
                r.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
                r.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
                r.setAudioEncodingBitRate(64000);
                r.setAudioSamplingRate(16000);
                r.setOutputFile(file.getAbsolutePath());
                r.prepare();
                r.start();
                recorder = r;
                Db.get(this).addLog("RECORD", "", "RECORDING", file.getName());
                return true;
            } catch (Exception e) {
                // try next source
            }
        }
        Db.get(this).addLog("RECORD", "", "RECORD_FAILED", "microphone busy or blocked by Android");
        return false;
    }

    @Override
    public void onDestroy() {
        if (recorder != null) {
            try { recorder.stop(); } catch (Exception ignored) { }
            try { recorder.release(); } catch (Exception ignored) { }
            recorder = null;
            if (file != null && file.exists() && file.length() < 2048) file.delete();
        }
        super.onDestroy();
    }
}
