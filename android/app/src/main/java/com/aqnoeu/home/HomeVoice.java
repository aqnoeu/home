package com.aqnoeu.home;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.media.MediaPlayer;
import android.speech.RecognizerIntent;
import android.speech.tts.TextToSpeech;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Locale;

/** Home Alex voice: use same Kokoro pm_alex synthesis as Windows via opt-in HTTPS server. */
public final class HomeVoice {
    public static final int REQUEST_SPEECH = 412;
    public static final String VOICE_ID = "pm_alex";
    private static final int MAX_WAV = 6000000;
    private static TextToSpeech systemTts;
    private static MediaPlayer player;
    private HomeVoice() {}

    public static void listen(Activity activity) {
        Intent intent=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE,"pt-BR");
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT,"Fale com o Home");
        try { activity.startActivityForResult(intent,REQUEST_SPEECH); }
        catch(Exception e) {Toast.makeText(activity,"Reconhecimento de voz indisponível.",Toast.LENGTH_LONG).show();}
    }

    public static void speak(Activity activity,String message) {
        final String text=message==null?"":message.trim();
        if(text.isEmpty())return;
        android.content.SharedPreferences prefs=activity.getSharedPreferences("home_ai",Context.MODE_PRIVATE);
        String endpoint=prefs.getString("endpoint","");
        String token=prefs.getString("token","");
        boolean preferAlex=activity.getSharedPreferences("home",Context.MODE_PRIVATE).getBoolean("voice_alex",true);
        if(preferAlex && endpoint.startsWith("https://") && !token.isEmpty()) {
            new Thread(()->fetchAlex(activity,text,endpoint,token)).start();
        } else {
            if(preferAlex) Toast.makeText(activity,
                "Alex (Kokoro) exige servidor de voz configurado. Usando voz temporária do Android.",
                Toast.LENGTH_LONG).show();
            speakWithSystem(activity,text);
        }
    }

    private static void fetchAlex(Activity activity,String text,String endpoint,String token) {
        File audio=new File(activity.getCacheDir(),"home_alex_"+System.nanoTime()+".wav");
        try {
            URL configured=new URL(endpoint);
            if(!"https".equals(configured.getProtocol()))throw new IOException("HTTPS obrigatório");
            URL url=new URL(configured.getProtocol(), configured.getHost(),
                configured.getPort(), "/tts");
            HttpURLConnection conn=(HttpURLConnection)url.openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(12000);
            conn.setReadTimeout(45000);
            conn.setRequestProperty("Authorization","Bearer "+token);
            conn.setRequestProperty("Content-Type","application/json");
            conn.setDoOutput(true);
            JSONObject request=new JSONObject();
            request.put("text",text.substring(0,Math.min(500,text.length())));
            request.put("rate",165);
            try(OutputStream out=conn.getOutputStream()){
                out.write(request.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
            }
            try {
                if(conn.getResponseCode()!=200)throw new IOException("Servidor da voz Alex: HTTP "+conn.getResponseCode());
                if(!conn.getContentType().toLowerCase(Locale.ROOT).startsWith("audio/wav"))
                    throw new IOException("Formato de voz inesperado");
                try(InputStream stream=conn.getInputStream();FileOutputStream output=new FileOutputStream(audio)){
                    byte[] buf=new byte[16384];int n,total=0;
                    while((n=stream.read(buf))!=-1){
                        total+=n;
                        if(total>MAX_WAV)throw new IOException("Áudio excede o limite");
                        output.write(buf,0,n);
                    }
                    if(total<44)throw new IOException("Áudio incompleto");
                }
            }finally{conn.disconnect();}
            activity.runOnUiThread(()->{
                if(activity.isFinishing()){audio.delete();return;}
                try {
                    if(player!=null){player.stop();player.release();}
                    player=new MediaPlayer();
                    player.setDataSource(audio.getAbsolutePath());
                    player.setOnCompletionListener(mp->{mp.release();audio.delete();if(player==mp)player=null;});
                    player.setOnErrorListener((mp,what,extra)->{mp.release();audio.delete();if(player==mp)player=null;return true;});
                    player.prepare();player.start();
                }catch(Exception e){audio.delete();speakWithSystem(activity,text);}
            });
        }catch(Exception ex) {
            audio.delete();
            activity.runOnUiThread(()->{
                if(activity.isFinishing())return;
                Toast.makeText(activity,"Voz Alex indisponível; usando voz temporária Android.",Toast.LENGTH_LONG).show();
                speakWithSystem(activity,text);
            });
        }
    }

    private static void speakWithSystem(Activity activity,String message) {
        if(systemTts==null){
            systemTts=new TextToSpeech(activity.getApplicationContext(),status->{
                if(status==TextToSpeech.SUCCESS && systemTts!=null){
                    systemTts.setLanguage(new Locale("pt","BR"));
                    systemTts.speak(message,TextToSpeech.QUEUE_FLUSH,null,"home_reply");
                }
            });
        }else systemTts.speak(message,TextToSpeech.QUEUE_FLUSH,null,"home_reply");
    }

    public static String localResponse(String phrase) {
        String message=phrase.toLowerCase(new Locale("pt","BR"));
        if(message.contains("bom dia")||message.contains("boa tarde")||message.contains("boa noite")||message.contains("olá")||message.equals("oi"))return "Olá! Que bom ouvir você!";
        if(message.contains("hora"))return "Agora são "+new java.text.SimpleDateFormat("HH:mm",new Locale("pt","BR")).format(new java.util.Date())+".";
        if(message.contains("como você está"))return "Estou muito feliz por estar aqui com você!";
        return "Eu ouvi: "+phrase+". Para uma resposta inteligente, conecte a IA nas configurações do Home.";
    }
}
