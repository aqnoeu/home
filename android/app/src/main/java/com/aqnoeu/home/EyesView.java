package com.aqnoeu.home;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Path;
import android.os.SystemClock;
import android.view.View;
import java.util.Random;

/** The approved HOME pair of rounded eyes, with subtle contextual states.
 * In-app expression colors never alter the official app icon/logo.
 * Motion reduces automatically when the OS animation scale is disabled.
 */
public final class EyesView extends View {
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Random random=new Random();
    private float eyeGapDp=9f;
    private long blinkAt=SystemClock.uptimeMillis()+3200,blinkStart=-1,nextLook=0,lastFrame=0;
    private float gaze=0,targetGaze=0,mix=1f;
    private float eyeHeight=1f,eyeWidth=1f,colorR=242,colorG=248,colorB=255;
    private String previousState="neutro";
    private int mood=0;
    public EyesView(Context context){super(context);setLayerType(View.LAYER_TYPE_SOFTWARE,null);}
    public void setEyeGap(float gap){eyeGapDp=Math.max(0,Math.min(600,gap));invalidate();}
    public void setMood(int index){
        mood=Math.max(0,Math.min(3,index));
        HomeEmotion.manual(index==2?"sonolento":index==3?"raiva":"neutro");
        invalidate();
    }
    private float dp(float value){return value*getResources().getDisplayMetrics().density;}
    private float lerp(float a,float b,float weight){return a+(b-a)*weight;}
    private boolean motionEnabled(){
        try{return android.provider.Settings.Global.getFloat(
            getContext().getContentResolver(),
            android.provider.Settings.Global.ANIMATOR_DURATION_SCALE,1f)>0f;}
        catch(Exception e){return true;}
    }
    @Override protected void onDraw(Canvas canvas){
        super.onDraw(canvas);
        long now=SystemClock.uptimeMillis();
        float dt=lastFrame==0?.05f:Math.min(.15f,(now-lastFrame)/1000f);
        lastFrame=now;
        boolean animated=motionEnabled();
        float smoothing=animated?1f-(float)Math.exp(-dt/0.23):1f;
        String state=HomeEmotion.current(getContext());
        android.content.SharedPreferences prefs=getContext().getSharedPreferences("home",Context.MODE_PRIVATE);
        String voice=prefs.getString("wake_visual_state","desligado");
        long stamped=prefs.getLong("wake_visual_at",0L);
        if(!prefs.getBoolean("wake_enabled",false) || System.currentTimeMillis()-stamped>120000L)
            voice="desligado";
        boolean listening="ouvindo".equals(voice);
        boolean commandListening="aguardando_comando".equals(voice);
        boolean speaking="falando".equals(voice);
        int rgb=Color.rgb(242,248,255);
        float targetH=1f,targetW=1f;
        if(listening || commandListening){
            rgb=Color.rgb(182,214,255);targetH=1.13f;targetW=1.02f;
        }else if(speaking){
            rgb=Color.rgb(255,196,136);targetH=.91f;
        }else if("raiva".equals(state)){rgb=Color.rgb(255,106,0);targetH=.83f;}
        else if("sonolento".equals(state)){rgb=Color.rgb(142,175,207);targetH=.38f;}
        else if("tedio".equals(state)){rgb=Color.rgb(139,149,164);targetH=.78f;targetW=.78f;}
        else if("carregando".equals(state)){rgb=Color.rgb(0,196,106);}
        else if("bateria_baixa".equals(state)){rgb=Color.rgb(242,164,68);targetH=.86f;}
        else if("economia".equals(state)){rgb=Color.rgb(147,184,219);targetH=.72f;}
        colorR=lerp(colorR,Color.red(rgb),smoothing);
        colorG=lerp(colorG,Color.green(rgb),smoothing);
        colorB=lerp(colorB,Color.blue(rgb),smoothing);
        eyeHeight=lerp(eyeHeight,targetH,smoothing);
        eyeWidth=lerp(eyeWidth,targetW,smoothing);
        if(listening || commandListening){
            targetGaze=0f;
            nextLook=now+500L;
        }else if(now>nextLook){
            targetGaze="tedio".equals(state)?(random.nextBoolean()?.35f:-.35f):
                (random.nextFloat()-.5f)*.65f;
            nextLook=now+("tedio".equals(state)?6000:3500)+random.nextInt(2100);
        }
        gaze=lerp(gaze,targetGaze,animated?.055f:1f);
        if(now>blinkAt&&blinkStart<0){blinkStart=now;blinkAt=now+4600+random.nextInt(3200);}
        float blink=1f;
        if(blinkStart>=0){
            float progress=(now-blinkStart)/380f;
            if(progress>=1)blinkStart=-1;
            else if(animated)blink=Math.max(.07f,1f-(float)Math.sin(progress*Math.PI)*.95f);
        }
        float width=getWidth(),height=getHeight();
        float ew=Math.min(dp(13),width*.12f)*eyeWidth;
        float voicePulse=(animated&&(listening||commandListening))
            ?(.89f+.11f*(float)Math.sin(now/185.0)):1f;
        float speechPulse=(animated&&speaking)
            ?(.91f+.09f*(float)Math.sin(now/235.0)):1f;
        float eh=Math.max(dp(3),Math.min(dp(21),height*.68f)*eyeHeight*blink*voicePulse*speechPulse);
        float gap=Math.min(dp(eyeGapDp),Math.max(0,width-2*ew-dp(8)));
        float left=(width-2*ew-gap)/2f+gaze*dp(6);
        int eyeColor=Color.rgb(Math.min(255,(int)colorR),Math.min(255,(int)colorG),Math.min(255,(int)colorB));
        float pulse="carregando".equals(state)&&animated
            ?(.93f+.07f*(float)Math.sin(now/550.0)):1f;
        paint.setColor(eyeColor);
        paint.setAlpha((int)(255*pulse));
        for(int i=0;i<2;i++){
            float x=left+i*(ew+gap);
            float shake="raiva".equals(state)&&animated?
                (float)Math.sin(now/44.0)*dp(.65f):0f;
            float y=(height-eh)/2f+shake;
            canvas.drawRoundRect(new RectF(x,y,x+ew,y+eh),
                Math.min(dp(5),eh/2),Math.min(dp(5),eh/2),paint);
            if("raiva".equals(state)&&eh>=dp(7)){
                Path lid=new Path();
                lid.moveTo(x-1,y-2);
                lid.lineTo(x+ew+1,y-2);
                if(i==0){lid.lineTo(x+ew+1,y+eh*.35f);lid.lineTo(x-1,y+eh*.08f);}
                else{lid.lineTo(x+ew+1,y+eh*.08f);lid.lineTo(x-1,y+eh*.35f);}
                lid.close();
                paint.setColor(Color.rgb(11,17,26));
                canvas.drawPath(lid,paint);
                paint.setColor(eyeColor);
            }else if(mood==1&&"neutro".equals(state)&&eh>=dp(9)){
                paint.setColor(Color.rgb(11,17,26));
                canvas.drawOval(new RectF(x-ew*.15f,y+eh*.54f,x+ew*1.16f,y+eh*1.36f),paint);
                paint.setColor(eyeColor);
            }
        }
        // Two gently oscillating indicators distinguish active listening from idle.
        if(listening || commandListening){
            paint.setAlpha(255);
            paint.setColor(commandListening?Color.rgb(255,177,91):Color.rgb(47,107,255));
            float wave=animated?(float)Math.sin(now/230.0):0f;
            float dot=dp(commandListening?2.1f:1.6f);
            float cy=Math.min(height-dp(3.1f),(height+eh)/2f+dp(3.3f));
            float spread=dp(2.6f)+dp(1.6f)*Math.abs(wave);
            canvas.drawCircle(width/2f-spread,cy-dot*.4f,dot,paint);
            canvas.drawCircle(width/2f+spread,cy+dot*.4f,dot,paint);
            paint.setAlpha(255);
        }else if(speaking){
            paint.setAlpha(255);
            paint.setColor(Color.rgb(255,106,0));
            float amplitude=animated?(.6f+.4f*Math.abs((float)Math.sin(now/195.0))):1f;
            canvas.drawRoundRect(new RectF(width/2f-dp(1.8f),height-dp(6)*amplitude,
                width/2f+dp(1.8f),height-dp(2)),dp(1.7f),dp(1.7f),paint);
        }
        // Scale sleepy marks to the compact notch too.
        if("sonolento".equals(state)&&height>=dp(20)){
            paint.setColor(Color.rgb(142,175,207));
            float scale=Math.max(.54f,Math.min(1f,height/dp(70)));
            float lift=animated?((now%3000L)/3000f)*dp(9)*scale:0;
            float sx=Math.min(width-dp(16)*scale,left+2*ew+gap+dp(5)*scale);
            paint.setTextSize(dp(11)*scale);
            canvas.drawText("z",sx,height*.59f-lift,paint);
            paint.setTextSize(dp(8)*scale);
            canvas.drawText("z",sx+dp(8)*scale,height*.37f-lift*.7f,paint);
        }
        if(animated)postInvalidateDelayed(50);
    }
}
