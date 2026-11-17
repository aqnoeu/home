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
    private final Runnable visualHeartbeat=new Runnable(){
        @Override public void run(){
            if(!running)return;
            android.content.SharedPreferences p=getSharedPreferences("home",MODE_PRIVATE);
            String current=p.getString("wake_visual_state","desligado");
            if(!"desligado".equals(current))visualState(current);
            main.postDelayed(this,30000L);
        }
    };
    private boolean backgroundWaiting, backgroundSpeaking;
    private final Runnable backgroundCommandTimeout=()->{
        if(backgroundWaiting && running && !paused){
            backgroundWaiting=false;
            visualState("detector_ativo");
            state("Nenhum comando ouvido. HOME voltou a escutar a palavra de ativação.");
        }
    };
    private boolean backgroundVoiceEnabled(){
        return getSharedPreferences("home",MODE_PRIVATE).getBoolean("wake_background_audio",false)
            && FaberOffline.isInstalled(this);
    }
    private void resetBackgroundState(){
        backgroundWaiting=false;
        backgroundSpeaking=false;
        main.removeCallbacks(backgroundCommandTimeout);
    }
    /** Tarefa curta com o detector já em execução. Não inicia outro microfone nem abre Activity. */
    private void beginBackgroundConversation(String initialCommand){
        String cmd=initialCommand==null?"":initialCommand.trim();
        if(!cmd.isEmpty()){
            replyBackground(cmd);
            return;
        }
        backgroundWaiting=true;
        visualState("aguardando_comando");
        state("HOME chamado em segundo plano. Aguardando comando por voz.");
        main.removeCallbacks(backgroundCommandTimeout);
        main.postDelayed(backgroundCommandTimeout,12000L);
    }
    private String offlineAnswer(String question){
        String q=normalize(question);
        Locale brazil=new Locale("pt","BR");
        java.util.Date now=new java.util.Date();
        if(q.matches(".*\\b(hora|horas|horario)\\b.*"))
            return "Agora são "+new java.text.SimpleDateFormat("HH:mm",brazil).format(now)+".";
        if(q.matches(".*\\b(data|dia de hoje|que dia e hoje|hoje e que dia)\\b.*"))
            return "Hoje é "+new java.text.SimpleDateFormat("dd 'de' MMMM 'de' yyyy",brazil).format(now)+".";
        if(q.matches(".*\\b(bateria|carga do celular|porcentagem)\\b.*"))
            return DeviceHub.battery(this);
        if(q.matches(".*\\b(wifi|wi fi|internet|rede)\\b.*"))
            return DeviceHub.network(this);
        if(q.matches(".*\\b(bluetooth)\\b.*"))
            return DeviceHub.bluetooth(this);
        if(q.matches(".*\\b(memoria|ram)\\b.*"))
            return DeviceHub.memory(this);
        if(q.matches(".*\\b(armazenamento|espaco livre)\\b.*"))
            return DeviceHub.storage();
        if(q.matches(".*\\b(ola|oi|bom dia|boa tarde|boa noite|tudo bem)\\b.*"))
            return "Olá! Estou ouvindo. Pode me chamar novamente.";
        return "Esse comando ainda precisa do chat do HOME. Você pode abrir o aplicativo para continuar.";
    }
    private void replyBackground(String command){
        if(!running || paused || backgroundSpeaking)return;
        backgroundWaiting=false;
        main.removeCallbacks(backgroundCommandTimeout);
        backgroundSpeaking=true;
        visualState("falando");
        paused=true;
        closeAudio(); // Faber não compete com o Vosk pelo microfone
        String answer=offlineAnswer(command);
        state("Respondendo em segundo plano com a Faber.");
        getSharedPreferences("home",MODE_PRIVATE).edit().putString("wake_last_command",command).apply();
        boolean started=FaberOffline.speakBackground(this,answer,()->main.post(()->{
            backgroundSpeaking=false;
            if(running && enabled(this)){
                paused=false;
                visualState("detector_ativo");
                consecutiveAudioErrors=0;
                main.postDelayed(()->{
                    if(running && !paused){
                        state("Faber terminou. HOME voltou a ouvir Ei Home ou Ok Home.");
                        beginListening();
                    }
                },1100L);
            }
        }));
        if(!started){
            backgroundSpeaking=false;
            paused=false;
            visualState("detector_ativo");
            state("A Faber não pôde responder. Detector reativado.");
            main.postDelayed(this::beginListening,1100L);
        }
    }
    private final Runnable pendingNotificationRecovery=()->{
        if(running && paused && !MainActivity.isInForeground()){
            paused=false;
            visualState("detector_ativo");
            clearPartial();
            state("HOME reativou a escuta após a notificação não ser aberta.");
            beginListening();
        }
    };

    public static boolean enabled(Context context) {
        return context.getSharedPreferences("home",MODE_PRIVATE).getBoolean("wake_enabled",false);
    }
    private void visualState(String visual){
        getSharedPreferences("home",MODE_PRIVATE).edit().putString("wake_visual_state",visual)
            .putLong("wake_visual_at",System.currentTimeMillis()).apply();
    }
    /** The green eyes indicate command capture, never passive wake-word detection. */
    public static void showCommandListening(Context context){
        context.getSharedPreferences("home",MODE_PRIVATE).edit()
            .putString("wake_visual_state","aguardando_comando")
            .putBoolean("wake_command_active",true)
            .putLong("wake_visual_at",System.currentTimeMillis()).apply();
    }
    public static void showProcessing(Context context){
        context.getSharedPreferences("home",MODE_PRIVATE).edit()
            .putString("wake_visual_state","processando")
            .putBoolean("wake_command_active",false)
            .putLong("wake_visual_at",System.currentTimeMillis()).apply();
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
        if(intent!=null && STOP.equals(intent.getAction())){resetBackgroundState();stopSelf();return START_NOT_STICKY;}
        if(!enabled(this) || !getSharedPreferences("home",MODE_PRIVATE).getBoolean("notch_active",false)
            || checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED
            || !WakeModelInstaller.installed(this)) {
            state("Ativação indisponível. Verifique o modelo, o Notch e a permissão do microfone.");
            stopSelf();return START_NOT_STICKY;
        }
        if(intent!=null && PAUSE.equals(intent.getAction())){
            resetBackgroundState();
            main.removeCallbacks(pendingNotificationRecovery);
            paused=true;
            visualState(getSharedPreferences("home",MODE_PRIVATE)
                .getBoolean("wake_command_active",false)?"aguardando_comando":"pausado");
            closeAudio();
            state("Detecção pausada durante a conversa.");
            if(running)return START_NOT_STICKY;
        }
        if(intent!=null && RESUME.equals(intent.getAction()) && running){
            if(backgroundSpeaking)return START_NOT_STICKY;
            resetBackgroundState();
            main.removeCallbacks(pendingNotificationRecovery);
            getSharedPreferences("home",MODE_PRIVATE).edit()
                .putBoolean("wake_command_active",false).apply();
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
        main.removeCallbacks(visualHeartbeat);
        main.postDelayed(visualHeartbeat,30000L);
        if(!paused)beginListening();
        return START_NOT_STICKY;
    }
    private void beginListening() {
        if(!running || paused || loading || audio!=null)return;
        if(model!=null){openAudio();return;}
        loading=true;
        visualState("carregando");
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
            visualState("detector_ativo");
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
        if(backgroundWaiting){
            if(partial)return;
            String suffixPending=activationSuffix(text,true);
            String command=suffixPending==null?text:suffixPending;
            if(!command.trim().isEmpty())replyBackground(command);
            return;
        }
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
        getSharedPreferences("home",MODE_PRIVATE).edit()
            .putLong("wake_last_recognized",System.currentTimeMillis()).apply();
        if(!MainActivity.isInForeground() && backgroundVoiceEnabled()){
            beginBackgroundConversation(command);
            return;
        }
        paused=true;
        visualState("pausado");
        closeAudio(); // libera o AudioRecord ANTES do microfone de conversa
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
        main.removeCallbacks(visualHeartbeat);
        resetBackgroundState();
        running=false;paused=true;
        getSharedPreferences("home",MODE_PRIVATE).edit()
            .putBoolean("wake_command_active",false).apply();
        visualState("desligado");
        closeAudio();
        if(model!=null){try{model.close();}catch(Exception ignored){}model=null;}
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent){return null;}
}
