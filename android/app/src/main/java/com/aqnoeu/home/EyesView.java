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
    // Shared expression IDs, preserving the original indices 0-3.
    public static final String[] EXPRESSION_LABELS={
        "Normal","Feliz","Sonolento","Bravo",
        "Piscadela","Lovabow","Pensando","Surpreso",
        "Desconfiado","Tímido","Confuso","Travesso"
    };
    public static final String[] EXPRESSION_KEYS={
        "neutro","feliz","sonolento","raiva",
        "piscadela","lovabow","pensando","surpreso",
        "desconfiado","timido","confuso","travesso"
    };
    private int mood=0;
    private boolean expressionPreview=false;
    private final android.content.SharedPreferences.OnSharedPreferenceChangeListener updateListener=
        (prefs,key)->{
            if(key!=null && key.startsWith("update_eyes_"))postInvalidateOnAnimation();
        };
    public EyesView(Context context){super(context);setLayerType(View.LAYER_TYPE_SOFTWARE,null);}
    @Override protected void onAttachedToWindow(){
        super.onAttachedToWindow();
        getContext().getSharedPreferences("home",Context.MODE_PRIVATE)
            .registerOnSharedPreferenceChangeListener(updateListener);
        postInvalidateOnAnimation();
    }
    @Override protected void onDetachedFromWindow(){
        getContext().getSharedPreferences("home",Context.MODE_PRIVATE)
            .unregisterOnSharedPreferenceChangeListener(updateListener);
        super.onDetachedFromWindow();
    }
    public void setEyeGap(float gap){eyeGapDp=Math.max(0,Math.min(600,gap));invalidate();}
    public void setMood(int index){
        mood=Math.max(0,Math.min(EXPRESSION_KEYS.length-1,index));
        if(!expressionPreview)HomeEmotion.manual(EXPRESSION_KEYS[mood]);
        invalidate();
    }
    /** Dedicated preview shows the chosen face even when charging/listening. */
    public void setExpressionPreview(boolean preview){
        expressionPreview=preview;
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
        android.content.SharedPreferences updatePrefs=getContext().getSharedPreferences("home",Context.MODE_PRIVATE);
        String updateState=updatePrefs.getString("update_eyes_state","idle");
        long updateChangedAt=updatePrefs.getLong("update_eyes_changed_at",0L);
        long updateElapsed=System.currentTimeMillis()-updateChangedAt;
        boolean updateDownloading=!expressionPreview && "downloading".equals(updateState) && updateElapsed>=0 && updateElapsed<3600000L;
        boolean updateComplete=!expressionPreview && "complete".equals(updateState) && updateElapsed>=0 && updateElapsed<2600L;
        boolean updateActive=!expressionPreview && (updateDownloading||updateComplete);
        float updateFraction=updateComplete?1f:
            Math.max(0f,Math.min(1f,updatePrefs.getInt("update_eyes_percent",0)/100f));
        float smoothing=animated?1f-(float)Math.exp(-dt/0.23):1f;
        String state=expressionPreview?EXPRESSION_KEYS[mood]:HomeEmotion.current(getContext());
        android.content.SharedPreferences prefs=getContext().getSharedPreferences("home",Context.MODE_PRIVATE);
        String voice=prefs.getString("wake_visual_state","desligado");
        long stamped=prefs.getLong("wake_visual_at",0L);
        if(expressionPreview || !prefs.getBoolean("wake_enabled",false) || System.currentTimeMillis()-stamped>120000L)
            voice="desligado";
        boolean listening="aguardando_comando".equals(voice);
        boolean commandListening=listening;
        boolean speaking="falando".equals(voice);
        boolean armed="armado".equals(voice) || "pausado".equals(voice) || "carregando".equals(voice);
        boolean activeConversation=!expressionPreview && HomeEmotion.isConversing() && HomeEmotion.enabled(getContext(),"conversa");
        boolean operational="carregando".equals(state)||"bateria_baixa".equals(state)||"economia".equals(state);
        int rgb=Color.rgb(242,248,255);
        float targetH=1f,targetW=1f;
        if(updateActive){
            rgb=Color.rgb(139,149,164);targetH=1f;targetW=1f; // cinza do tédio, preenchimento branco desenhado abaixo
        }else if((listening || commandListening) && HomeEmotion.enabled(getContext(),"escutando")){
            rgb=Color.rgb(45,255,90);targetH=1.13f;targetW=1.02f; // verde-neon, expressão feliz
        }else if(speaking && HomeEmotion.enabled(getContext(),"falando")){
            rgb=Color.WHITE;targetH=1f;targetW=1f; // fala da Faber: olhos brancos
        }else if(operational){
            if("carregando".equals(state))rgb=Color.rgb(0,196,106);
            else if("bateria_baixa".equals(state)){rgb=Color.rgb(242,164,68);targetH=.86f;}
            else {rgb=Color.rgb(147,184,219);targetH=.72f;}
        }else if(activeConversation && ("neutro".equals(state)||"feliz".equals(state)||"conversa".equals(state))){rgb=Color.rgb(45,220,112);targetH=1.05f;}
        else if(armed && "neutro".equals(state) && HomeEmotion.enabled(getContext(),"escutando") && !activeConversation){rgb=Color.WHITE;targetH=1f;targetW=1f;}
        else if("raiva".equals(state)){rgb=Color.rgb(255,106,0);targetH=.83f;}
        else if("sonolento".equals(state)){rgb=Color.rgb(142,175,207);targetH=.38f;}
        else if("tedio".equals(state)){rgb=Color.rgb(139,149,164);targetH=.78f;targetW=.78f;}
        else if("carregando".equals(state)){rgb=Color.rgb(0,196,106);}
        else if("bateria_baixa".equals(state)){rgb=Color.rgb(242,164,68);targetH=.86f;}
        else if("economia".equals(state)){rgb=Color.rgb(147,184,219);targetH=.72f;}
        else if("lovabow".equals(state)){rgb=Color.rgb(242,248,255);targetH=1f;}
        else if("pensando".equals(state)){rgb=Color.rgb(213,228,245);targetH=.76f;targetW=.92f;}
        else if("surpreso".equals(state)){rgb=Color.WHITE;targetH=1.12f;targetW=1.06f;}
        else if("desconfiado".equals(state)){rgb=Color.rgb(221,232,248);targetH=.82f;targetW=.9f;}
        else if("timido".equals(state)){rgb=Color.rgb(232,196,212);targetH=.8f;targetW=.94f;}
        else if("confuso".equals(state)){rgb=Color.rgb(223,233,248);targetH=.9f;targetW=.96f;}
        else if("travesso".equals(state)){rgb=Color.rgb(242,248,255);targetH=.84f;targetW=.94f;}
        // Escuta/fala são sinais imediatos, não transições suaves.
        float voiceSmoothing=(updateActive || listening || commandListening || speaking)?1f:smoothing;
        colorR=lerp(colorR,Color.red(rgb),voiceSmoothing);
        colorG=lerp(colorG,Color.green(rgb),voiceSmoothing);
        colorB=lerp(colorB,Color.blue(rgb),voiceSmoothing);
        eyeHeight=lerp(eyeHeight,targetH,smoothing);
        eyeWidth=lerp(eyeWidth,targetW,smoothing);
        if(updateActive || listening || commandListening){
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
        // Só durante a resposta falada: pulso suave dos olhos brancos.
        float speakingPulse=speaking&&animated
            ?(0.91f+0.09f*(float)Math.sin(now/210.0)):1f;
        float eh=Math.max(dp(3),Math.min(dp(21),height*.68f)*eyeHeight*blink*speakingPulse);
        float gap=Math.min(dp(eyeGapDp),Math.max(0,width-2*ew-dp(8)));
        float left=(width-2*ew-gap)/2f+gaze*dp(6);
        int eyeColor=Color.rgb(Math.min(255,(int)colorR),Math.min(255,(int)colorG),Math.min(255,(int)colorB));
        float pulse=!updateActive && "carregando".equals(state)&&animated
            ?(.93f+.07f*(float)Math.sin(now/550.0)):1f;
        paint.setColor(eyeColor);
        paint.setAlpha((int)(255*pulse));
        for(int i=0;i<2;i++){
            float x=left+i*(ew+gap);
            float shake="raiva".equals(state)&&animated?
                (float)Math.sin(now/44.0)*dp(.65f):0f;
            float oneH=eh;
            if("piscadela".equals(state)&&i==0)oneH*=.12f;
            else if("confuso".equals(state))oneH*=i==0?.65f:1.08f;
            else if("desconfiado".equals(state))oneH*=i==0?.62f:.96f;
            else if("travesso".equals(state))oneH*=i==0?.55f:.92f;
            if("pensando".equals(state))x+=ew*.12f;
            float y=(height-oneH)/2f+shake;
            // At 100% only the RIGHT eye winks once, and the ordinary emotion returns.
            if(updateComplete && i==1 && updateElapsed>=700 && updateElapsed<1150){
                float phase=(updateElapsed-700f)/450f;
                float wink=animated?Math.max(.09f,1f-(float)Math.sin(Math.PI*phase)*.91f):.12f;
                y+=(eh-eh*wink)/2f;
                float winkHeight=eh*wink;
                paint.setColor(Color.WHITE);
                paint.setAlpha(255);
                canvas.drawRoundRect(new RectF(x,y,x+ew,y+winkHeight),
                    Math.min(dp(5),winkHeight/2f),Math.min(dp(5),winkHeight/2f),paint);
                paint.setColor(eyeColor);
            }else if(updateActive){
                RectF eyeBounds=new RectF(x,y,x+ew,y+eh);
                float radius=Math.min(dp(5),eh/2f);
                paint.setColor(Color.rgb(139,149,164)); // same gray as tédio
                paint.setAlpha(255);
                canvas.drawRoundRect(eyeBounds,radius,radius,paint);
                int saved=canvas.save();
                Path mask=new Path();
                mask.addRoundRect(eyeBounds,radius,radius,Path.Direction.CW);
                canvas.clipPath(mask);
                float fillTop=y+eh*(1f-updateFraction);
                if(updateFraction>0f){
                    paint.setColor(Color.WHITE);
                    paint.setShadowLayer(dp(2.5f),0f,0f,Color.WHITE);
                    canvas.drawRect(x,fillTop,x+ew,y+eh,paint);
                    paint.clearShadowLayer();
                }
                canvas.restoreToCount(saved);
                paint.setColor(eyeColor);
            }else if("lovabow".equals(state)){
                // Original two-eye identity, with each eye shaped as a heart.
                float phase=animated?(now%1800L)/1800f:1f;
                int rose=phase<.30f?Color.rgb(242,248,255):
                    phase<.60f?Color.rgb(246,174,200):Color.rgb(241,139,181);
                paint.setColor(rose);
                paint.setAlpha(255);
                Path heart=new Path();
                heart.moveTo(x+ew*.50f,y+oneH*.94f);
                heart.cubicTo(x-ew*.14f,y+oneH*.58f,x-ew*.10f,y+oneH*.12f,x+ew*.26f,y+oneH*.12f);
                heart.cubicTo(x+ew*.43f,y+oneH*.12f,x+ew*.50f,y+oneH*.30f,x+ew*.50f,y+oneH*.30f);
                heart.cubicTo(x+ew*.50f,y+oneH*.30f,x+ew*.57f,y+oneH*.12f,x+ew*.74f,y+oneH*.12f);
                heart.cubicTo(x+ew*1.10f,y+oneH*.12f,x+ew*1.14f,y+oneH*.58f,x+ew*.50f,y+oneH*.94f);
                heart.close();
                canvas.drawPath(heart,paint);
                paint.setColor(eyeColor);
            }else{
                canvas.drawRoundRect(new RectF(x,y,x+ew,y+oneH),
                    Math.min(dp(5),oneH/2),Math.min(dp(5),oneH/2),paint);
            }
            if(!updateActive && "raiva".equals(state)&&eh>=dp(7)){
                Path lid=new Path();
                lid.moveTo(x-1,y-2);
                lid.lineTo(x+ew+1,y-2);
                if(i==0){lid.lineTo(x+ew+1,y+eh*.35f);lid.lineTo(x-1,y+eh*.08f);}
                else{lid.lineTo(x+ew+1,y+eh*.08f);lid.lineTo(x-1,y+eh*.35f);}
                lid.close();
                paint.setColor(Color.rgb(11,17,26));
                canvas.drawPath(lid,paint);
                paint.setColor(eyeColor);
            }else if(!(updateComplete && i==1 && updateElapsed>=700 && updateElapsed<1150) &&
                ((updateActive || listening || commandListening) || ("feliz".equals(state)))&&eh>=dp(9)){
                paint.setColor(Color.rgb(11,17,26));
                canvas.drawOval(new RectF(x-ew*.15f,y+eh*.54f,x+ew*1.16f,y+eh*1.36f),paint);
                paint.setColor(eyeColor);
            }
        }
        // Pontinhos acompanham exclusivamente a fala, nunca a escuta verde-neon.
        if(speaking && !updateActive){
            paint.setColor(Color.WHITE);
            paint.setAlpha(255);
            float center=width/2f;
            float baseline=Math.min(height-dp(2.0f),height/2f+eh/2f+dp(3.0f));
            float radius=dp(1.3f);
            for(int i=0;i<3;i++){
                float phase=(float)(now/205.0-i*0.85);
                float lift=animated?dp(1.6f)*Math.max(0f,(float)Math.sin(phase)):0f;
                canvas.drawCircle(center+(i-1)*dp(4f),baseline-lift,radius,paint);
            }
        }
        if("lovabow".equals(state)&&height>=dp(34) && animated){
            float phase=(now%1800L)/1800f;
            if(phase>.55f){
                paint.setColor(Color.rgb(241,139,181));
                float base=left+2*ew+gap+dp(5);
                for(int i=0;i<3;i++){
                    float x=base+i*dp(4), y=height*.66f-(phase-.55f)*height*.8f-i*dp(3);
                    Path small=new Path();
                    small.moveTo(x,y+dp(3));
                    small.cubicTo(x-dp(5),y,x-dp(3),y-dp(3),x,y-dp(1));
                    small.cubicTo(x+dp(3),y-dp(3),x+dp(5),y,x,y+dp(3));
                    small.close();
                    canvas.drawPath(small,paint);
                }
            }
        }
        if(animated || updateActive)postInvalidateDelayed(50);
    }
}
