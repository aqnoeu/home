package com.aqnoeu.home;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.View;
import java.util.Random;

/** Eyes geometry follows Home's PySide6 EyesWidget: two soft white rounded bars. */
public final class EyesView extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Random random = new Random();
    private int mood = 0;
    private float eyeGapDp = 9f;
    private long blinkAt = android.os.SystemClock.uptimeMillis() + 3500;
    private long blinkStart = -1;
    private float gaze = 0, targetGaze = 0;
    private long nextLook = 0;
    public EyesView(Context context) { super(context); setLayerType(View.LAYER_TYPE_SOFTWARE, null); }
    public void setEyeGap(float gap) { eyeGapDp = Math.max(0,Math.min(260,gap)); invalidate(); }
    public void setMood(int mood) { this.mood = Math.max(0, Math.min(3, mood)); invalidate(); }
    private float dp(float v) { return v * getResources().getDisplayMetrics().density; }
    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        final long now = android.os.SystemClock.uptimeMillis();
        if (now > nextLook) { targetGaze = (random.nextFloat() - .5f) * .7f; nextLook = now + 3500 + random.nextInt(3500); }
        gaze += (targetGaze - gaze) * .06f;
        if (now > blinkAt && blinkStart < 0) { blinkStart = now; blinkAt = now + 4500 + random.nextInt(3500); }
        float blink = 1f;
        if (blinkStart >= 0) {
            float progress = (now-blinkStart)/380f;
            if (progress >= 1) blinkStart = -1;
            else blink = Math.max(.07f, 1f-(float)Math.sin(progress*Math.PI)*.95f);
        }
        if (mood == 2) blink *= .54f;
        float width = getWidth(), height = getHeight();
        float ew = Math.min(dp(13), width * .12f), eh = Math.min(dp(21), height * .68f) * blink;
        float gap = Math.min(dp(eyeGapDp), Math.max(0,width - 2 * ew - dp(8)));
        float left = (width - 2 * ew - gap)/2f + gaze * dp(6);
        paint.setColor(Color.rgb(242,248,255));
        for(int i=0;i<2;i++) {
            float x=left+i*(ew+gap), y=(height-eh)/2f;
            canvas.drawRoundRect(new RectF(x,y,x+ew,y+eh), Math.min(dp(5),eh/2),Math.min(dp(5),eh/2),paint);
            if(mood==1 && blink>.6f) {
                paint.setColor(Color.rgb(5,7,11));
                canvas.drawOval(new RectF(x-ew*.17f,y+eh*.49f,x+ew*1.17f,y+eh*1.3f),paint);
                paint.setColor(Color.rgb(242,248,255));
            }
        }
        postInvalidateDelayed(50);
    }
}
