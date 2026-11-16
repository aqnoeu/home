package com.aqnoeu.home;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.*;
import org.json.JSONObject;
import org.vosk.Model;
import org.vosk.Recognizer;
import org.vosk.android.RecognitionListener;
import org.vosk.android.SpeechService;
import java.text.Normalizer;
import java.util.Locale;

/**
 * Uma única sessão contínua Vosk local para a frase "Ei Home" / "Ok Home".
 * Não usa SpeechRecognizer, não reinicia o microfone após silêncio nem envia áudio.
 * O reconhecimento completo do comando permanece separado em HomeVoice.
 */
public final class WakeWordService extends Service implements RecognitionListener {
    public static final String STOP="com.aqnoeu.home.WAKE_STOP";
    public static final String PAUSE="com.aqnoeu.home.WAKE_PAUSE";
    public static final String RESUME="com.aqnoeu.home.WAKE_RESUME";
    public static final String EXTRA_QUERY="com.aqnoeu.home.WAKE_QUERY";
    private final Handler main=new Handler(Looper.getMainLooper());
    private Model model;
    private Recognizer recognizer;
    private SpeechService audio;
    private boolean running,paused,loading;
    private long lastWakeAt;

    public static boolean enabled(Context context) {
        return context.getSharedPreferences("home",MODE_PRIVATE).getBoolean("wake_enabled",false);
    }
    private void state(String value) {
        getSharedPreferences("home",MODE_PRIVATE).edit().putString("wake_status",value).apply();
    }
    @Override public void onCreate() {
        super.onCreate();
        NotificationManager nm=getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("home_wake","HOME — Ativação por voz",NotificationManager.IMPORTANCE_LOW));
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId) {
        if(intent!=null && STOP.equals(intent.getAction())){stopSelf();return START_NOT_STICKY;}
        if(!enabled(this) || !getSharedPreferences("home",MODE_PRIVATE).getBoolean("notch_active",false)
            || checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED
            || !WakeModelInstaller.installed(this)) {
            state("Ativação indisponível. Verifique o modelo, o Notch e a permissão do microfone.");
            stopSelf();return START_NOT_STICKY;
        }
        if(intent!=null && PAUSE.equals(intent.getAction())){
            paused=true;
            closeAudio();
            state("Detecção pausada durante a conversa.");
            if(running)return START_NOT_STICKY;
        }
        if(intent!=null && RESUME.equals(intent.getAction()) && running){
            paused=false;
            beginListening();
            return START_NOT_STICKY;
        }
        if(running)return START_NOT_STICKY;
        Intent app=new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent tap=PendingIntent.getActivity(this,72,app,
            PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification notification=new Notification.Builder(this,"home_wake")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("HOME — Ei Home ou Ok Home")
            .setContentText("Detecção de voz local ativa. Toque para abrir o HOME.")
            .setContentIntent(tap).setOngoing(true).build();
        try{
            if(Build.VERSION.SDK_INT>=29)startForeground(72,notification,
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
            else startForeground(72,notification);
        }catch(RuntimeException ex){
            state("O Android impediu o início do microfone: "+ex.getClass().getSimpleName());
            stopSelf();return START_NOT_STICKY;
        }
        running=true;
        if(!paused)beginListening();
        return START_NOT_STICKY;
    }
    private void beginListening() {
        if(!running || paused || loading || audio!=null)return;
        if(model!=null){openAudio();return;}
        loading=true;
        state("Carregando detector local de português...");
        new Thread(()->{
            Model loaded=null;
            try {loaded=new Model(WakeModelInstaller.folder(this).getAbsolutePath());}
            catch(Exception ex){
                state("Falha ao carregar modelo offline: "+ex.getClass().getSimpleName());
                main.post(this::stopSelf);
                return;
            }finally { main.post(()->loading=false); }
            Model ready=loaded;
            main.post(()->{
                if(!running){ready.close();return;}
                model=ready;
                if(!paused)openAudio();
            });
        },"home-wake-vosk-init").start();
    }
    private void openAudio() {
        if(!running || paused || audio!=null || model==null)return;
        try{
            recognizer=new Recognizer(model,16000.0f);
            audio=new SpeechService(recognizer,16000.0f);
            if(!audio.startListening(this))throw new IllegalStateException("Não foi possível iniciar a escuta.");
            state("Aguardando Ei Home ou Ok Home (offline).");
        }catch(Exception ex){
            state("Falha no microfone offline: "+ex.getClass().getSimpleName());
            closeAudio();stopSelf();
        }
    }
    private void closeAudio(){
        SpeechService current=audio;
        audio=null;
        if(current!=null){
            try{current.cancel();}catch(Exception ignored){}
            try{current.shutdown();}catch(Exception ignored){}
        }
        if(recognizer!=null){
            try{recognizer.close();}catch(Exception ignored){}
            recognizer=null;
        }
    }
    private String normalize(String input){
        return Normalizer.normalize(input.toLowerCase(new Locale("pt","BR")),Normalizer.Form.NFD)
            .replaceAll("\\p{M}+","").replaceAll("[^a-z0-9 ]+"," ").replaceAll("\\s+"," ").trim();
    }
    private void detect(String hypothesis){
        if(!running || paused || hypothesis==null)return;
        String text;
        try{text=normalize(new JSONObject(hypothesis).optString("text",""));}
        catch(Exception ignored){return;}
        if(text.isEmpty())return;
        String[] triggers={"ei home","ok home","hey home","oi home"};
        int end=-1;
        for(String trigger:triggers){
            if(text.equals(trigger) || text.startsWith(trigger+" ")){end=trigger.length();break;}
        }
        if(end<0 || SystemClock.elapsedRealtime()-lastWakeAt<4000)return;
        lastWakeAt=SystemClock.elapsedRealtime();
        String command=text.substring(end).trim();
        paused=true;
        closeAudio(); // libera o AudioRecord ANTES do microfone de conversa
        state("Ativado. Ouvindo seu comando.");
        Intent open=new Intent(this,MainActivity.class)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP)
            .putExtra(EXTRA_QUERY,command);
        try{startActivity(open);}
        catch(RuntimeException ex){
            state("Toque na notificação HOME para abrir a conversa.");
            PendingIntent pending=PendingIntent.getActivity(this,73,open,
                PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
            Notification note=new Notification.Builder(this,"home_wake")
                .setContentTitle("HOME foi chamado")
                .setContentText("Toque para conversar.")
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setContentIntent(pending).setAutoCancel(true).build();
            getSystemService(NotificationManager.class).notify(73,note);
        }
    }
    @Override public void onResult(String hypothesis){detect(hypothesis);}
    @Override public void onPartialResult(String hypothesis){} // não ativar com hipóteses parciais instáveis
    @Override public void onFinalResult(String hypothesis){detect(hypothesis);}
    @Override public void onError(Exception error){
        if(!running || paused)return;
        state("Detector local interrompido: "+error.getClass().getSimpleName()+". Reative no HOME.");
        stopSelf(); // sem laços de reinicialização automática
    }
    @Override public void onTimeout(){} // modo sem timeout
    @Override public void onDestroy(){
        running=false;paused=true;
        closeAudio();
        if(model!=null){try{model.close();}catch(Exception ignored){}model=null;}
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent){return null;}
}
