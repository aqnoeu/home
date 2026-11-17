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
    private long audioGeneration;
    private int consecutiveAudioErrors;
    private String partialCandidate="";
    private int partialCount;
    private long partialSince;
    private final Runnable pendingNotificationRecovery=()->{
        if(running && paused && !MainActivity.isInForeground()){
            paused=false;
            clearPartial();
            state("HOME reativou a escuta após a notificação não ser aberta.");
            beginListening();
        }
    };

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
            main.removeCallbacks(pendingNotificationRecovery);
            paused=true;
            closeAudio();
            state("Detecção pausada durante a conversa.");
            if(running)return START_NOT_STICKY;
        }
        if(intent!=null && RESUME.equals(intent.getAction()) && running){
            main.removeCallbacks(pendingNotificationRecovery);
            consecutiveAudioErrors=0;
            paused=false;
            clearPartial();
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
            final long generation=++audioGeneration;
            RecognitionListener sessionListener=new RecognitionListener(){
                @Override public void onResult(String text){if(generation==audioGeneration)detect(text,false);}
                @Override public void onPartialResult(String text){if(generation==audioGeneration)detect(text,true);}
                @Override public void onFinalResult(String text){if(generation==audioGeneration)detect(text,false);}
                @Override public void onError(Exception e){if(generation==audioGeneration)WakeWordService.this.onError(e);}
                @Override public void onTimeout(){if(generation==audioGeneration)WakeWordService.this.onTimeout();}
            };
            if(!audio.startListening(sessionListener))throw new IllegalStateException("Não foi possível iniciar a escuta.");
            state("Detector offline ouvindo. Diga Ei Home, Ok Home ou Home.");
        }catch(Exception ex){
            state("Falha no microfone offline: "+ex.getClass().getSimpleName());
            closeAudio();stopSelf();
        }
    }
    private void closeAudio(){
        audioGeneration++; // invalida resultados e erros atrasados da sessão encerrada
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
    /** Reconhece apenas frases de ativação, inclusive variantes ditadas com HOME antes da saudação. */
    static String activationSuffix(String phrase,boolean finalOnly){
        String text=phrase.trim();
        String[] prefix={"ei home","ok home","hey home","oi home","ei romi","ei rome",
            "ok romi","ok rome","o que home","home ok home","home ei home","home","home home"};
        for(String value:prefix){
            if(value.equals("home") && !finalOnly)continue; // "Home" isolado exige resultado final
            if(text.equals(value))return "";
            if(text.startsWith(value+" "))return text.substring(value.length()).trim();
        }
        return null;
    }
    private void clearPartial(){
        partialCandidate="";
        partialCount=0;
        partialSince=0;
    }
    private void detect(String hypothesis,boolean partial){
        if(!running || paused || hypothesis==null)return;
        String text;
        try{text=normalize(new JSONObject(hypothesis).optString(partial?"partial":"text",""));}
        catch(Exception ignored){return;}
        if(text.isEmpty())return;
        String suffix=activationSuffix(text,!partial);
        if(suffix==null){if(!partial)clearPartial();return;}
        long now=SystemClock.elapsedRealtime();
        if(now-lastWakeAt<4000)return;
        if(partial){
            // Requer 3 confirmações estáveis em pelo menos 200 ms; nunca usa texto incompleto como comando.
            String matched=text.contains("home ok home")?"home ok home":
                text.contains("home ei home")?"home ei home":
                text.startsWith("ei home")?"ei home":
                text.startsWith("ok home")?"ok home":
                text.startsWith("hey home")?"hey home":
                text.startsWith("oi home")?"oi home":
                text.startsWith("o que home")?"o que home":text.startsWith("ei rom")?"ei rome":
                text.startsWith("ok rom")?"ok rome":null;
            if(matched==null)return;
            if(!matched.equals(partialCandidate)){partialCandidate=matched;partialCount=1;partialSince=now;return;}
            partialCount++;
            if(partialCount<3 || now-partialSince<200)return;
            suffix=""; // abrir reconhecimento completo, não reaproveitar hipótese parcial
        }
        clearPartial();
        activate(suffix);
    }
    private void activate(String command){
        lastWakeAt=SystemClock.elapsedRealtime();
        paused=true;
        closeAudio(); // libera o AudioRecord ANTES do microfone de conversa
        getSharedPreferences("home",MODE_PRIVATE).edit()
            .putLong("wake_last_recognized",System.currentTimeMillis()).apply();
        Intent open=new Intent(this,MainActivity.class)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP)
            .putExtra(EXTRA_QUERY,command);
        if(MainActivity.isInForeground()){
            try{
                state("Ativação reconhecida. Abrindo microfone de conversa.");
                startActivity(open);
                return;
            }catch(RuntimeException ex){
                state("Reconhecido, mas o Android impediu a abertura automática.");
            }
        }
        // O Android limita iniciar Activity em segundo plano, mesmo com Foreground Service.
        // Oferece notificação de alta prioridade que permite a transição por toque autorizado.
        state("Home reconheceu a frase. Toque na notificação para conversar.");
        PendingIntent tap=PendingIntent.getActivity(this,73,open,
            PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        NotificationManager manager=getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel(
            "home_wake_detected_v2","HOME — Chamado por voz",NotificationManager.IMPORTANCE_HIGH));
        Notification note=new Notification.Builder(this,"home_wake_detected_v2")
            .setContentTitle("HOME ouviu você")
            .setContentText("Toque para abrir a conversa.")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(tap)
            .setAutoCancel(true)
            .setCategory(Notification.CATEGORY_MESSAGE)
            .addAction(new Notification.Action.Builder(
                android.R.drawable.ic_btn_speak_now,"Conversar",tap).build())
            .build();
        manager.notify(73,note);
        // A notificação pode não ser tocada. Não deixe o detector permanentemente pausado.
        main.removeCallbacks(pendingNotificationRecovery);
        main.postDelayed(pendingNotificationRecovery,20000L);
    }
    @Override public void onResult(String hypothesis){detect(hypothesis,false);}
    @Override public void onPartialResult(String hypothesis){detect(hypothesis,true);}
    @Override public void onFinalResult(String hypothesis){detect(hypothesis,false);}
    @Override public void onError(Exception error){
        if(!running || paused)return;
        if(consecutiveAudioErrors>=1){
            state("Detector local indisponível após nova tentativa: "+error.getClass().getSimpleName());
            stopSelf();
            return;
        }
        consecutiveAudioErrors++;
        state("Microfone interrompido. Tentando restabelecer a escuta uma vez.");
        main.post(()->{
            if(!running || paused)return;
            closeAudio();
            main.postDelayed(()->{
                if(running && !paused)beginListening();
            },1400L);
        });
    }
    @Override public void onTimeout(){} // modo sem timeout
    @Override public void onDestroy(){
        main.removeCallbacks(pendingNotificationRecovery);
        running=false;paused=true;
        closeAudio();
        if(model!=null){try{model.close();}catch(Exception ignored){}model=null;}
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent){return null;}
}
