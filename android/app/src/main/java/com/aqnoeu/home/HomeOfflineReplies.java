package com.aqnoeu.home;

import java.util.Locale;

/**
 * Offline responses allowed in background, independent of the microphone
 * session, visual state and foreground Activity. No Groq/network calls.
 */
public final class HomeOfflineReplies {
    private HomeOfflineReplies() {}
    public static String answer(android.content.Context context,String question){
        String q=java.text.Normalizer.normalize(question.toLowerCase(new Locale("pt","BR")),java.text.Normalizer.Form.NFD)
            .replaceAll("\\p{M}+","").replaceAll("[^a-z0-9 ]+"," ").replaceAll("\\s+"," ").trim();
        Locale brazil=new Locale("pt","BR");
        java.util.Date now=new java.util.Date();
        if(q.matches(".*\\b(hora|horas|horario)\\b.*"))
            return "Agora são "+new java.text.SimpleDateFormat("HH:mm",brazil).format(now)+".";
        if(q.matches(".*\\b(data|dia de hoje|que dia e hoje|hoje e que dia)\\b.*"))
            return "Hoje é "+new java.text.SimpleDateFormat("dd 'de' MMMM 'de' yyyy",brazil).format(now)+".";
        if(q.matches(".*\\b(bateria|carga do celular|porcentagem)\\b.*"))
            return DeviceHub.battery(context);
        if(q.matches(".*\\b(wifi|wi fi|internet|rede)\\b.*"))
            return DeviceHub.network(context);
        if(q.matches(".*\\b(bluetooth)\\b.*"))
            return DeviceHub.bluetooth(context);
        if(q.matches(".*\\b(memoria|ram)\\b.*"))
            return DeviceHub.memory(context);
        if(q.matches(".*\\b(armazenamento|espaco livre)\\b.*"))
            return DeviceHub.storage();
        if(q.matches(".*\\b(ola|oi|bom dia|boa tarde|boa noite|tudo bem)\\b.*"))
            return "Olá! Estou ouvindo. Pode me chamar novamente.";
        return "Esse comando ainda precisa do chat do HOME. Você pode abrir o aplicativo para continuar.";
    }
}
