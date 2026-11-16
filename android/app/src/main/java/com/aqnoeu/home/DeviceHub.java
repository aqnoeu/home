package com.aqnoeu.home;

import android.app.ActivityManager;
import android.app.AlarmManager;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.AudioDeviceInfo;
import android.media.AudioManager;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Environment;
import android.os.StatFs;
import android.provider.AlarmClock;
import android.provider.CalendarContract;
import android.provider.Settings;
import java.util.Locale;

/** Explicit, foreground-only platform queries. Never sends device data to Groq. */
public final class DeviceHub {
    private DeviceHub() {}
    private static String bytes(long value) {
        if(value<0)return "indisponível";
        double gib=value/(1024.0*1024*1024);
        return String.format(new Locale("pt","BR"),"%.1f GB",gib);
    }
    public static String battery(Context context){
        Intent state=context.registerReceiver(null,new android.content.IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if(state==null)return "Bateria: estado indisponível.";
        int level=state.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
        int scale=state.getIntExtra(BatteryManager.EXTRA_SCALE,-1);
        if(level<0||scale<=0)return "Bateria: estado indisponível.";
        int percent=Math.round(100f*level/scale);
        int plug=state.getIntExtra(BatteryManager.EXTRA_PLUGGED,0);
        int status=state.getIntExtra(BatteryManager.EXTRA_STATUS,-1);
        String condition=(status==BatteryManager.BATTERY_STATUS_FULL)?"carga completa":
            plug!=0?"conectado à energia":"usando bateria";
        return "Bateria: "+percent+"% · "+condition+".";
    }
    public static String network(Context context){
        try{
            ConnectivityManager manager=(ConnectivityManager)context.getSystemService(Context.CONNECTIVITY_SERVICE);
            if(manager==null)return "Rede: indisponível.";
            Network network=manager.getActiveNetwork();
            if(network==null)return "Rede: sem conexão ativa.";
            NetworkCapabilities caps=manager.getNetworkCapabilities(network);
            if(caps==null)return "Rede: não consegui identificar o tipo.";
            String kind=caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)?"Wi-Fi":
                caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)?"dados móveis":
                caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)?"Ethernet":
                caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN)?"VPN":"outra conexão";
            boolean validated=caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);
            return "Rede: "+kind+" · "+(validated?"acesso à internet validado pelo Android":
                "sem validação de acesso à internet")+".";
        }catch(SecurityException ex){return "Rede: permissão de estado não concedida.";}
    }
    public static String bluetooth(Context context){
        try{
            BluetoothManager manager=(BluetoothManager)context.getSystemService(Context.BLUETOOTH_SERVICE);
            if(manager==null)return "Bluetooth indisponível.";
            BluetoothAdapter adapter=manager.getAdapter();
            if(adapter==null)return "Este aparelho não dispõe de Bluetooth.";
            if(Build.VERSION.SDK_INT>=31 &&
                context.checkSelfPermission(android.Manifest.permission.BLUETOOTH_CONNECT)!=PackageManager.PERMISSION_GRANTED)
                return "Bluetooth: conceda acesso a dispositivos próximos para consultar o estado.";
            return "Bluetooth "+(adapter.isEnabled()?"ligado.":"desligado.");
        }catch(SecurityException ex){return "Bluetooth: permissão necessária.";}
    }
    public static String audio(Context context){
        AudioManager manager=(AudioManager)context.getSystemService(Context.AUDIO_SERVICE);
        if(manager==null)return "Áudio indisponível.";
        int volume=manager.getStreamVolume(AudioManager.STREAM_MUSIC);
        int max=manager.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
        int percent=max>0?Math.round(100f*volume/max):0;
        String output="alto-falante do aparelho";
        for(AudioDeviceInfo d:manager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)){
            if(d.getType()==AudioDeviceInfo.TYPE_BLUETOOTH_A2DP ||
               d.getType()==AudioDeviceInfo.TYPE_BLUETOOTH_SCO ||
               (Build.VERSION.SDK_INT>=31 && d.getType()==AudioDeviceInfo.TYPE_BLE_HEADSET)){
                output="fone ou caixa Bluetooth";break;
            }
            if(d.getType()==AudioDeviceInfo.TYPE_WIRED_HEADPHONES ||
               d.getType()==AudioDeviceInfo.TYPE_WIRED_HEADSET ||
               d.getType()==AudioDeviceInfo.TYPE_USB_HEADSET)output="fone conectado";
        }
        return "Áudio: "+percent+"% · saída detectada: "+output+".";
    }
    public static String memory(Context context){
        ActivityManager manager=(ActivityManager)context.getSystemService(Context.ACTIVITY_SERVICE);
        if(manager==null)return "Memória indisponível.";
        ActivityManager.MemoryInfo info=new ActivityManager.MemoryInfo();
        manager.getMemoryInfo(info);
        return "Memória RAM disponível: "+bytes(info.availMem)+" de "+bytes(info.totalMem)+".";
    }
    public static String storage(){
        try{
            StatFs stats=new StatFs(Environment.getDataDirectory().getPath());
            return "Armazenamento interno livre: "+bytes(stats.getAvailableBytes())+
                " de "+bytes(stats.getTotalBytes())+".";
        }catch(Exception ex){return "Armazenamento indisponível.";}
    }
    /** Clipboard is accessed only after tapping a button while the Activity is foreground. */
    public static String clipboard(Context context){
        ClipboardManager cb=(ClipboardManager)context.getSystemService(Context.CLIPBOARD_SERVICE);
        if(cb==null || !cb.hasPrimaryClip())return "Área de transferência vazia.";
        ClipData clip=cb.getPrimaryClip();
        if(clip==null || clip.getItemCount()==0)return "Área de transferência vazia.";
        CharSequence value=clip.getItemAt(0).coerceToText(context);
        if(value==null)return "Não há texto disponível.";
        String result=value.toString().trim();
        return result.isEmpty()?"Não há texto disponível.":result.substring(0,Math.min(700,result.length()));
    }
    public static String overview(Context context){
        return battery(context)+"\n"+network(context)+"\n"+bluetooth(context)+"\n"+
            audio(context)+"\n"+memory(context)+"\n"+storage();
    }
    public static Intent calendarIntent(){
        Intent i=new Intent(Intent.ACTION_MAIN);
        i.addCategory(Intent.CATEGORY_APP_CALENDAR);
        return i;
    }
    public static Intent newEventIntent(){
        return new Intent(Intent.ACTION_INSERT,CalendarContract.Events.CONTENT_URI);
    }
    public static Intent alarmsIntent(){
        return new Intent(AlarmClock.ACTION_SHOW_ALARMS);
    }
    public static Intent soundSettings(){
        return new Intent(Settings.ACTION_SOUND_SETTINGS);
    }
    public static Intent bluetoothSettings(){
        return new Intent(Settings.ACTION_BLUETOOTH_SETTINGS);
    }
}
