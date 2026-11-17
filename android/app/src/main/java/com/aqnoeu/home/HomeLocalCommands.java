package com.aqnoeu.home;

import android.content.Context;
import android.provider.Settings;
import java.text.Normalizer;
import java.util.Date;
import java.util.Locale;

/**
 * Pure command routing and read-only device lookups.
 * This class deliberately does NOT perform UI navigation, execute app actions,
 * persist chat, access an AI provider or start a microphone.
 * Those effects remain in MainActivity following explicit user actions.
 */
public final class HomeLocalCommands {
    private HomeLocalCommands() {}
    public static final class Result {
        public final String answer;
        public final String setting;
        Result(String answer,String setting){this.answer=answer;this.setting=setting;}
    }
    public static Result resolve(Context context,String query){
        String q=query==null?"":query.trim().toLowerCase(java.util.Locale.ROOT);
        String normalized=java.text.Normalizer.normalize(q,java.text.Normalizer.Form.NFD)
            .replaceAll("\\p{M}+","");
        String answer=null;
        String setting=null;
        if(normalized.matches(".*\\b(que horas|quantas horas|qual a hora|qual e a hora|horario atual|qual o horario|me diga as horas|me diz as horas|me fale as horas|diga as horas|sao que horas)\\b.*")
            || normalized.matches("^(horas|hora|horario|as horas|me diga a hora|me diz a hora|me fale a hora)[?!. ]*$")){
            answer="Agora são "+new java.text.SimpleDateFormat("HH:mm",
                new java.util.Locale("pt","BR")).format(new Date())+".";
        }else if(normalized.matches(".*\\b(que dia e hoje|qual a data|data de hoje|dia de hoje)\\b.*")){
            answer="Hoje é "+new java.text.SimpleDateFormat("dd/MM/yyyy",
                new java.util.Locale("pt","BR")).format(new Date())+".";
        }else if(normalized.matches(".*\\b(bateria|nivel da bateria|carga do celular)\\b.*")){
            answer=DeviceHub.battery(context);
        }else if(normalized.matches(".*\\b(rede|internet|conexao wi-?fi|sinal wi-?fi)\\b.*")){
            answer=DeviceHub.network(context);
        }else if(normalized.matches(".*\\b(memoria ram|ram disponivel|uso da memoria)\\b.*")){
            answer=DeviceHub.memory(context);
        }else if(normalized.matches(".*\\b(armazenamento|espaco livre|espaco no celular)\\b.*")){
            answer=DeviceHub.storage();
        }else if(normalized.matches(".*\\b(volume atual|volume da midia|nivel do volume)\\b.*")){
            answer=DeviceHub.audio(context);
        }else if(normalized.matches(".*\\b(bluetooth esta|estado do bluetooth|status do bluetooth)\\b.*")){
            answer=DeviceHub.bluetooth(context);
        }else if(normalized.matches("^(abra|abrir|abre|mostrar|mostre)\\s+(as\\s+)?(configuracoes\\s+(do|de)\\s+)?(wi-?fi|wifi).*")){
            answer="Abrindo as configurações de Wi-Fi.";
            setting=Settings.ACTION_WIFI_SETTINGS;
        }else if(normalized.matches("^(abra|abrir|abre|mostrar|mostre)\\s+(as\\s+)?(configuracoes\\s+(do|de)\\s+)?bluetooth.*")){
            answer="Abrindo as configurações de Bluetooth.";
            setting=Settings.ACTION_BLUETOOTH_SETTINGS;
        }else return null;
        return new Result(answer,setting);
    }
}
