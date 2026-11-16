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
    private View touchHandle;
    private WindowManager.LayoutParams handleParams;
    private WindowManager.LayoutParams layoutParams;
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
        layoutParams = new WindowManager.LayoutParams(
            dp(116), dp(34), WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT);
        layoutParams.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL;
        if (Build.VERSION.SDK_INT >= 28) {
            layoutParams.layoutInDisplayCutoutMode =
                WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        }
        updatePosition(false);
        try {
            manager.addView(overlay,layoutParams);
            createTouchHandle(show);
        } catch (RuntimeException ex) {
            if (overlay != null) try { manager.removeView(overlay); } catch (Exception ignored) {}
            overlay = null; stopSelf();
        }
    }
    /** A small visible touch tab sits BELOW the system bar, while eyes stay near the top. */
    private void createTouchHandle(Intent show) {
        TextViewOpenButton tab = new TextViewOpenButton(this);
        tab.setText("⌃");
        tab.setTextColor(Color.rgb(242,248,255));
        tab.setTextSize(14);
        tab.setGravity(Gravity.CENTER);
        GradientDrawable background = new GradientDrawable();
        background.setColor(Color.rgb(5,7,11));
        background.setCornerRadii(new float[]{0,0,0,0,dp(12),dp(12),dp(12),dp(12)});
        tab.setBackground(background);
        tab.setOnClickListener(v -> startActivity(show));
        touchHandle=tab;
        handleParams = new WindowManager.LayoutParams(
            dp(52), dp(22), WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT);
        handleParams.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL;
        repositionHandle();
        manager.addView(touchHandle,handleParams);
    }
    private static final class TextViewOpenButton extends android.widget.TextView {
        TextViewOpenButton(Context c) { super(c); }
    }
    private int statusBarHeight() {
        int dimension = getResources().getIdentifier("status_bar_height","dimen","android");
        return dimension > 0 ? getResources().getDimensionPixelSize(dimension) : dp(26);
    }
    private void repositionHandle() {
        if (handleParams == null) return;
        android.content.SharedPreferences prefs = getSharedPreferences("home",MODE_PRIVATE);
        handleParams.x = dp(Math.max(-180,Math.min(180,prefs.getInt("offset_x",100))));
        // A reliable interactive region below the top system bar.
        handleParams.y = statusBarHeight() + dp(Math.max(0,Math.min(48,prefs.getInt("handle_y",4))));
        boolean enabled = prefs.getBoolean("touch_tab",true);
        if (touchHandle != null) {
            touchHandle.setVisibility(enabled ? View.VISIBLE : View.GONE);
            if (manager != null) try {manager.updateViewLayout(touchHandle,handleParams);}
            catch(RuntimeException ignored) {}
        }
    }
    // Android/HyperOS may still clamp overlays to below the status bar.
    private void updatePosition(boolean apply) {
        if (layoutParams == null) return;
        android.content.SharedPreferences prefs = getSharedPreferences("home",MODE_PRIVATE);
        int offsetX = prefs.getInt("offset_x",100);
        int offsetY = prefs.getInt("offset_y",0);
        boolean edge = prefs.getBoolean("edge_mode",true);
        int statusBar = 0;
        int dimension = getResources().getIdentifier("status_bar_height","dimen","android");
        if (dimension > 0) statusBar = getResources().getDimensionPixelSize(dimension);
        layoutParams.x = dp(Math.max(-180,Math.min(180,offsetX)));
        layoutParams.y = (edge ? -statusBar : 0) + dp(Math.max(-60,Math.min(40,offsetY)));
        if (apply && overlay != null && manager != null) {
            try { manager.updateViewLayout(overlay,layoutParams); }
            catch (RuntimeException ignored) { /* May be blocked by system UI. */ }
        }
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId) {
        if (intent != null && STOP.equals(intent.getAction())) { stopSelf(); return START_NOT_STICKY; }
        if (overlay instanceof EyesView) ((EyesView)overlay).setMood(getSharedPreferences("home",MODE_PRIVATE).getInt("mood",0));
        updatePosition(true);
        repositionHandle();
        return START_STICKY;
    }
    @Override public void onDestroy() {
        if (touchHandle != null && manager != null) {try {manager.removeView(touchHandle);} catch(Exception ignored){} touchHandle = null; }
        if (overlay != null && manager != null) { try {manager.removeView(overlay);} catch(Exception ignored){} overlay = null; }
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent) { return null; }
}
