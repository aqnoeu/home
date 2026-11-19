package com.aqnoeu.home;

import android.content.Context;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/** Explicit allowlist for Groq-requested, read-only operations on the current device.
 * No writes, credentials, notifications, clipboard, calendar content or API calls.
 */
public final class HomeLocalActions {
    private HomeLocalActions(){}
    public static String readOnly(Context context,String action){
        if(action==null)return null;
        try {
            switch(action.trim().toLowerCase(Locale.ROOT)){
                case "hora": return "Agora são "+new SimpleDateFormat("HH:mm",new Locale("pt","BR")).format(new Date())+".";
                case "data": return "Hoje é "+new SimpleDateFormat("dd/MM/yyyy",new Locale("pt","BR")).format(new Date())+".";
                case "bateria": return DeviceHub.battery(context);
                case "rede": return DeviceHub.network(context);
                case "bluetooth": return DeviceHub.bluetooth(context);
                case "memoria": return DeviceHub.memory(context);
                case "armazenamento": return DeviceHub.storage();
                case "audio": return DeviceHub.audio(context);
                default: return null;
            }
        }catch(SecurityException ex){
            return "Preciso de autorização do Android para consultar essa informação. Abra Home Connect.";
        }catch(Exception ex){
            return "Não consegui consultar esse recurso no dispositivo agora.";
        }
    }
}
