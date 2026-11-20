package com.aqnoeu.home;

import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.BatteryManager;
import android.os.PowerManager;
import android.os.SystemClock;
import java.util.concurrent.atomic.AtomicLong;

/** No accessibility service, monitoring other apps or background recording.
 * Phone inactivity is based on interactions with HOME and screen state.
 */
public final class HomeEmotion {
    private static final AtomicLong LAST_TOUCH=new AtomicLong(SystemClock.elapsedRealtime());
    private static volatile long conversationUntil=0L;
    private static volatile String conversational="neutro";
    private static volatile String manual="neutro";
    private static volatile String activePage="";
    private static volatile long pageSince=SystemClock.elapsedRealtime();
    private HomeEmotion(){}
    /** Disabled native expressions are hidden, not removed from the renderer. */
    public static boolean enabled(Context context,String state){
        return context.getSharedPreferences("home_emotion_controls",Context.MODE_PRIVATE)
            .getBoolean("emotion_"+state,true);
    }
    public static void setEnabled(Context context,String state,boolean value){
        context.getSharedPreferences("home_emotion_controls",Context.MODE_PRIVATE)
            .edit().putBoolean("emotion_"+state,value).apply();
    }
    public static boolean isConversing(){
        return SystemClock.elapsedRealtime()<conversationUntil;
    }

    public static void touch(){LAST_TOUCH.set(SystemClock.elapsedRealtime());}
    public static void pageChanged(String page){
        if(page==null)page="";
        if(!page.equals(activePage)){
            activePage=page;
            pageSince=SystemClock.elapsedRealtime();
            touch();
        }
    }
    public static void manual(String emotion){
        manual=normalize(emotion);
        conversationUntil=0;
        touch();
    }
    public static void fromGroq(String emotion){
        conversational=normalize(emotion);
        conversationUntil=SystemClock.elapsedRealtime()+16000L;
        touch();
    }
    public static String normalize(String emotion){
        if("feliz".equals(emotion)||"raiva".equals(emotion)||"sonolento".equals(emotion)||"tedio".equals(emotion)
            ||"piscadela".equals(emotion)||"lovabow".equals(emotion)
            ||"pensando".equals(emotion)||"surpreso".equals(emotion)
            ||"desconfiado".equals(emotion)||"timido".equals(emotion)
            ||"confuso".equals(emotion)||"travesso".equals(emotion))
            return emotion;
        return "neutro";
    }
    private static boolean charging(Context c) {
        try {
            Intent battery=c.registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            if(battery==null)return false;
            int state=battery.getIntExtra(BatteryManager.EXTRA_STATUS,-1);
            int present=battery.getIntExtra(BatteryManager.EXTRA_PRESENT,1);
            return present==1&&(state==BatteryManager.BATTERY_STATUS_CHARGING
                                ||state==BatteryManager.BATTERY_STATUS_FULL);
        }catch(Exception ignored){return false;}
    }
    private static boolean batteryLow(Context context){
        try{
            Intent battery=context.registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            if(battery==null)return false;
            int level=battery.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
            int scale=battery.getIntExtra(BatteryManager.EXTRA_SCALE,-1);
            int plugged=battery.getIntExtra(BatteryManager.EXTRA_PLUGGED,0);
            return scale>0 && level>=0 && plugged==0 &&
                (100f*level/scale)<=20f;
        }catch(Exception ignored){return false;}
    }
    private static boolean powerSaving(Context context){
        PowerManager power=(PowerManager)context.getSystemService(Context.POWER_SERVICE);
        return power!=null && power.isPowerSaveMode();
    }
    public static String current(Context context){
        long now=SystemClock.elapsedRealtime();
        // Safety/operational states retain priority over temporary manual reactions.
        if(charging(context)&&enabled(context,"carregando"))return "carregando";
        if(batteryLow(context)&&enabled(context,"bateria_baixa"))return "bateria_baixa";
        if(powerSaving(context)&&enabled(context,"economia"))return "economia";
        android.content.SharedPreferences preferences=context.getSharedPreferences("home",Context.MODE_PRIVATE);
        if(preferences.getBoolean("expression_fixed",false)){
            long started=preferences.getLong("expression_selected_at",0L);
            // Elapsed realtime does not survive a reboot: a future timestamp is invalid.
            if(started>0 && now>=started && now-started<30000L){
                int selected=preferences.getInt("mood",0);
                if(selected>=0 && selected<EyesView.EXPRESSION_KEYS.length){
                    String chosen=EyesView.EXPRESSION_KEYS[selected];
                    if(enabled(context,chosen))return chosen;
                }
            }
            preferences.edit().putBoolean("expression_fixed",false).apply();
        }
        if(now<conversationUntil){
            if(enabled(context,conversational))return conversational;
            if(enabled(context,"conversa"))return "conversa";
            return "neutro";
        }
        if(now-LAST_TOUCH.get()>=5*60*1000L && enabled(context,"sonolento"))return "sonolento";
        if(now-pageSince>=12*60*1000L && enabled(context,"tedio"))return "tedio";
        if(enabled(context,manual))return manual;
        for(String fallback:EyesView.EXPRESSION_KEYS)
            if(enabled(context,fallback))return fallback;
        return "neutro";
    }
}
