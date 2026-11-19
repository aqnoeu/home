package com.aqnoeu.home;

import android.content.Context;
import android.content.SharedPreferences;

/** Accurate, read-only Home feature catalog for the conversational model.
 * Never includes credentials, account content, clipboard or personal calendar events.
 */
public final class HomeCapabilities {
    private HomeCapabilities(){}
    public static String describe(Context context) {
        SharedPreferences prefs=context.getSharedPreferences("home",Context.MODE_PRIVATE);
        StringBuilder result=new StringBuilder(
            "Recursos reais do HOME Android: hora e data locais offline; consultas de bateria, rede, Bluetooth, memória RAM, armazenamento e volume; "
            +"abrir configurações de Wi-Fi e Bluetooth; abrir agenda e criar evento no aplicativo de agenda; "
            +"ler compromissos de hoje somente com permissão e pedido expresso; "
            +"gerenciar notificações autorizadas; notch animado; ativação por voz local; "
            +"conversas salvas; Groq para respostas conversacionais; atualizações mediante confirmação. "
            +"O Home Connect oferece cadastro local de perfis de API com credenciais criptografadas, "
            +"mas não executa chamadas a APIs personalizadas e não acessa contas externas automaticamente. "
            +"Nunca afirme ter executado comando ou lido dados que não foram fornecidos. "
            +"Quando o usuário pedir uma ação fora dos comandos locais disponíveis, explique como fazê-la na interface HOME.");
        result.append(" Estado das preferências: notch ")
            .append(prefs.getBoolean("notch_active",false)?"ativado":"desativado")
            .append("; ativação Ei Home ")
            .append(prefs.getBoolean("wake_enabled",false)?"ativada":"desativada")
            .append("; Groq ").append(HomeGroq.connected(context)?"conectada":"desconectada").append(".");
        if(prefs.getBoolean("home_connect_share_device_state",false)){
            result.append(" Estado básico do dispositivo compartilhado com consentimento: ")
                .append(DeviceHub.battery(context)).append(" ")
                .append(DeviceHub.network(context)).append(".");
        }
        return result.toString();
    }
}
