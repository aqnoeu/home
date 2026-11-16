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
        if("raiva".equals(emotion)||"sonolento".equals(emotion)||"tedio".equals(emotion))
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
        if(now<conversationUntil)return conversational;
        if(charging(context))return "carregando";
        if(batteryLow(context))return "bateria_baixa";
        if(powerSaving(context))return "economia";
        if(now-LAST_TOUCH.get()>=5*60*1000L)return "sonolento";
        // Without Accessibility permission, observe only the HOME screen itself.
        if(now-pageSince>=12*60*1000L)return "tedio";
        return manual;
    }
}
