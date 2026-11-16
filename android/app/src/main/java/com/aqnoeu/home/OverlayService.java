package com.aqnoeu.home;

import android.app.*;
import android.content.*;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.IBinder;
import android.provider.Settings;
import android.view.*;

public final class OverlayService extends Service {
    public static final String STOP = "com.aqnoeu.home.STOP";
    private WindowManager manager;
    private View overlay;
    private final int notificationId = 71;
    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    @Override public void onCreate() {
        super.onCreate();
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("home_notch","Home — Notch",NotificationManager.IMPORTANCE_LOW));
        Intent show = new Intent(this, MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent open = PendingIntent.getActivity(this,1,show,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        Notification note = new Notification.Builder(this,"home_notch")
            .setContentTitle("Home ativo").setContentText("Toque para abrir ou desativar o Notch")
            .setSmallIcon(android.R.drawable.ic_menu_view).setContentIntent(open).setOngoing(true).build();
        startForeground(notificationId,note);
        if (!Settings.canDrawOverlays(this)) { stopSelf(); return; }
        manager = (WindowManager)getSystemService(WINDOW_SERVICE);
        EyesView eyes = new EyesView(this);
        eyes.setMood(getSharedPreferences("home",MODE_PRIVATE).getInt("mood",0));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.rgb(5,7,11));
        bg.setCornerRadii(new float[]{0,0,0,0,dp(18),dp(18),dp(18),dp(18)});
        eyes.setBackground(bg);
        eyes.setOnClickListener(v->startActivity(show));
        overlay = eyes;
        WindowManager.LayoutParams params = new WindowManager.LayoutParams(
            dp(150),dp(40),WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE|WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT);
        params.gravity = Gravity.TOP|Gravity.CENTER_HORIZONTAL;
        // Overlay coordinates obey Android's status-bar/cutout restrictions.
        params.y = 0;
        try { manager.addView(overlay,params); }
        catch (RuntimeException ex) { overlay = null; stopSelf(); }
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId) {
        if (intent != null && STOP.equals(intent.getAction())) { stopSelf(); return START_NOT_STICKY; }
        if (overlay instanceof EyesView) ((EyesView)overlay).setMood(getSharedPreferences("home",MODE_PRIVATE).getInt("mood",0));
        return START_STICKY;
    }
    @Override public void onDestroy() {
        if (overlay != null && manager != null) { try {manager.removeView(overlay);} catch(Exception ignored){} overlay = null; }
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent) { return null; }
}
