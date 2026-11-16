package com.aqnoeu.home;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.*;
import android.speech.*;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Locale;

/**
 * Opt-in wake phrase while the user-enabled notch is running.
 * Uses Android SpeechRecognizer: recognition may be processed by the device's speech provider.
 * Not a low-power/offline hotword engine; restarts after silence and recoverable errors.
 */
public final class WakeWordService extends Service {
    public static final String STOP = "com.aqnoeu.home.WAKE_STOP";
    public static final String RESUME = "com.aqnoeu.home.WAKE_RESUME";
    public static final String PAUSE = "com.aqnoeu.home.WAKE_PAUSE";
    public static final String EXTRA_QUERY = "com.aqnoeu.home.WAKE_QUERY";
    private final Handler handler = new Handler(Looper.getMainLooper());
    private SpeechRecognizer recognizer;
    private boolean running, paused, listening;
    private long lastWakeAt=0;
    private int failures;
    private final Runnable restart = this::listen;

    public static boolean enabled(Context c) {
        return c.getSharedPreferences("home",MODE_PRIVATE).getBoolean("wake_enabled",false);
    }
    @Override public void onCreate() {
        super.onCreate();
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("home_wake","Home — Ativação por voz",NotificationManager.IMPORTANCE_LOW));
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId) {
        if(intent!=null && STOP.equals(intent.getAction())) { stopSelf(); return START_NOT_STICKY; }
        if(!enabled(this) || !getSharedPreferences("home",MODE_PRIVATE).getBoolean("notch_active",false)
            || checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED) {
            stopSelf(); return START_NOT_STICKY;
        }
        if(intent!=null && PAUSE.equals(intent.getAction())) {
            paused=true;
            handler.removeCallbacks(restart);
            if(recognizer!=null){recognizer.cancel();listening=false;}
            state("Em pausa durante a conversa.");
            if(running)return START_NOT_STICKY;
        }
        if(intent!=null && RESUME.equals(intent.getAction()) && running) {
            paused=false; failures=0; listening=false; schedule(1700); return START_NOT_STICKY;
        }
        if(running) return START_NOT_STICKY;
        Notification note = new Notification.Builder(this,"home_wake")
            .setContentTitle("Ei, Home ativado").setContentText("Microfone aguardando a frase de ativação")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(PendingIntent.getActivity(this,2,
                new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT))
            .setOngoing(true).build();
        try {
            if(Build.VERSION.SDK_INT>=29) startForeground(72,note,android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
            else startForeground(72,note);
        } catch(RuntimeException e) { stopSelf(); return START_NOT_STICKY; }
        running=true;
        if(!SpeechRecognizer.isRecognitionAvailable(this)) {
            state("Reconhecimento de voz não disponível no Android.");stopSelf();return START_NOT_STICKY;
        }
        recognizer=SpeechRecognizer.createSpeechRecognizer(this);
        recognizer.setRecognitionListener(new RecognitionListener() {
            public void onReadyForSpeech(Bundle b) { state("Microfone pronto. Diga Ei, Home."); failures=0; }
            public void onBeginningOfSpeech() {}
            public void onRmsChanged(float v) {}
            public void onBufferReceived(byte[] b) {}
            public void onEndOfSpeech() {}
            // Partial hypotheses fluctuate and may falsely contain a wake phrase.
            public void onPartialResults(Bundle b) {}
            public void onResults(Bundle b) {
                listening=false;
                if(!paused)detect(b);
                schedule(2400);
            }
            public void onError(int error) {
                listening=false;
                if(!running || paused) return;
                // Permission/recognizer errors must not cause a rapid retry loop.
                if(error==SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS) {
                    state("Sem permissão para o microfone."); stopSelf(); return;
                }
                state("Reconhecimento interrompido (código "+error+"). Nova tentativa automática.");
                failures=Math.min(failures+1,6);
                schedule(Math.min(20000,2600*(1<<Math.min(failures,3))));
            }
            public void onEvent(int event,Bundle params) {}
        });
        if(!paused)schedule(300);
        return START_NOT_STICKY;
    }
    private String normalize(String s) {
        return Normalizer.normalize(s.toLowerCase(new Locale("pt","BR")),Normalizer.Form.NFD)
            .replaceAll("\\p{M}+","");
    }
    private void detect(Bundle bundle) {
        if(paused || bundle==null)return;
        long now=android.os.SystemClock.elapsedRealtime();
        if(now-lastWakeAt<12000)return;
        ArrayList<String> phrases=bundle.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if(phrases==null)return;
        for(String phrase:phrases){
            if(phrase==null)continue;
            String normalized=normalize(phrase).trim().replaceAll("^[^a-z0-9]+","");
            String[] triggers={"ei home","hey home","oi home","ok home"};
            for(String trigger:triggers){
                if(!normalized.equals(trigger) && !normalized.startsWith(trigger+" ") &&
                    !normalized.startsWith(trigger+",") && !normalized.startsWith(trigger+"!") &&
                    !normalized.startsWith(trigger+"?") && !normalized.startsWith(trigger+"."))continue;
                lastWakeAt=now;
                paused=true;
                listening=false;
                state("Chamada Ei, Home reconhecida.");
                handler.removeCallbacks(restart);
                if(recognizer!=null)recognizer.cancel();
                String query=normalized.substring(trigger.length()).replaceFirst("^[^a-z0-9]+","").trim();
                Intent open=new Intent(this,MainActivity.class)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP)
                    .putExtra(EXTRA_QUERY,query);
                try{startActivity(open);}catch(RuntimeException ex){
                    state("Toque no Notch para abrir o assistente.");
                    paused=false;schedule(4500);
                }
                return;
            }
        }
    }
    private void state(String value){
        getSharedPreferences("home",MODE_PRIVATE).edit().putString("wake_status",value).apply();
    }
    private void schedule(long delayMs) {
        handler.removeCallbacks(restart);
        if(running && !paused) handler.postDelayed(restart,delayMs);
    }
    private void listen() {
        if(!running || paused || listening || recognizer==null) return;
        try {
            Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,"pt-BR");
            i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,true);
            i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS,3);
            listening=true;
            recognizer.startListening(i);
        } catch(RuntimeException e) {
            listening=false;
            state("Falha na escuta: "+e.getClass().getSimpleName());
            failures++; schedule(3000);
        }
    }
    @Override public void onDestroy() {
        running=false; handler.removeCallbacks(restart);
        if(recognizer!=null) {recognizer.cancel();recognizer.destroy();recognizer=null;}
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent) {return null;}
}
