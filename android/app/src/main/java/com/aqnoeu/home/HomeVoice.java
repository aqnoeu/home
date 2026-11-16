package com.aqnoeu.home;

import android.app.Activity;
import android.content.Intent;
import android.widget.Toast;
import android.speech.RecognizerIntent;
import java.util.Locale;

/** Voice input only. Voice output uses local Faber Piper. */
public final class HomeVoice {
    public static final int REQUEST_SPEECH = 412;
    private HomeVoice() {}

    public static void listen(Activity activity) {
        Intent intent=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE,"pt-BR");
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT,"Fale com o Home");
        try { activity.startActivityForResult(intent,REQUEST_SPEECH); }
        catch(Exception e) {Toast.makeText(activity,"Reconhecimento de voz indisponível neste aparelho.",Toast.LENGTH_LONG).show();}
    }

    public static void speak(Activity activity,String message) {
        FaberOffline.speak(activity,message,status ->
            Toast.makeText(activity,status,Toast.LENGTH_SHORT).show());
    }

    public static String localResponse(String phrase) {
        String message=phrase.toLowerCase(new Locale("pt","BR"));
        if(message.contains("bom dia")||message.contains("boa tarde")||message.contains("boa noite")||message.contains("olá")||message.equals("oi"))return "Olá! Que bom ouvir você!";
        if(message.contains("hora"))return "Agora são "+new java.text.SimpleDateFormat("HH:mm",new Locale("pt","BR")).format(new java.util.Date())+".";
        if(message.contains("como você está"))return "Estou muito feliz por estar aqui com você!";
        return "Ainda não estou conectado a uma inteligência artificial para responder perguntas abertas. Por enquanto, posso dizer as horas e reagir a saudações.";
    }
}
