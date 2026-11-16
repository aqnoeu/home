package com.aqnoeu.home;

import android.app.Notification;
import android.app.PendingIntent;
import android.content.Intent;
import android.os.Bundle;
import android.app.RemoteInput;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import java.util.ArrayList;
import java.util.List;

/** Opt-in notification access: reads only when the user explicitly opens the panel.
 * No persistence, telemetry, background summaries or Groq transmission.
 */
public final class HomeNotifications extends NotificationListenerService {
    private static volatile HomeNotifications active;
    @Override public void onListenerConnected(){super.onListenerConnected();active=this;}
    @Override public void onListenerDisconnected(){
        if(active==this)active=null;
        super.onListenerDisconnected();
    }
    @Override public void onDestroy(){if(active==this)active=null;super.onDestroy();}
    public static boolean connected(){return active!=null;}
    public static final class Item {
        public final String source;
        public final String title;
        public final String content;
        public final Notification.Action reply;
        public Item(String source,String title,String content,Notification.Action reply){
            this.source=source;this.title=title;this.content=content;this.reply=reply;
        }
        @Override public String toString(){return source+" · "+title+
            (content.isEmpty()?"":"\n"+content);}
    }
    public static List<Item> snapshot(){
        ArrayList<Item> result=new ArrayList<>();
        HomeNotifications service=active;
        if(service==null)return result;
        StatusBarNotification[] notifications;
        try{notifications=service.getActiveNotifications();}
        catch(SecurityException ex){return result;}
        if(notifications==null)return result;
        for(int index=notifications.length-1;index>=0 && result.size()<10;index--){
            StatusBarNotification bar=notifications[index];
            Notification note=bar.getNotification();
            if(note==null || note.extras==null)continue;
            String title=String.valueOf(note.extras.getCharSequence(Notification.EXTRA_TITLE,"")).trim();
            String content=String.valueOf(note.extras.getCharSequence(Notification.EXTRA_TEXT,"")).trim();
            if(title.isEmpty() && content.isEmpty())continue;
            Notification.Action action=null;
            if(note.actions!=null)for(Notification.Action candidate:note.actions){
                if(candidate==null || candidate.actionIntent==null || candidate.getRemoteInputs()==null)continue;
                for(RemoteInput input:candidate.getRemoteInputs()){
                    if(input.getAllowFreeFormInput()){action=candidate;break;}
                }
                if(action!=null)break;
            }
            result.add(new Item(bar.getPackageName(),title.substring(0,Math.min(title.length(),100)),
                content.substring(0,Math.min(content.length(),240)),action));
        }
        return result;
    }
    /** Trigger only after user types text AND explicitly confirms in the HOME UI. */
    public static boolean sendReply(Item item,String message){
        HomeNotifications service=active;
        if(service==null || item==null || item.reply==null || message==null ||
            message.trim().isEmpty() || message.length()>500)return false;
        try{
            RemoteInput[] inputs=item.reply.getRemoteInputs();
            Bundle results=new Bundle();
            for(RemoteInput input:inputs)if(input.getAllowFreeFormInput())
                results.putCharSequence(input.getResultKey(),message.trim());
            if(results.isEmpty())return false;
            Intent fill=new Intent();
            RemoteInput.addResultsToIntent(inputs,fill,results);
            item.reply.actionIntent.send(service,0,fill);
            return true;
        }catch(PendingIntent.CanceledException | SecurityException ex){return false;}
    }
}
