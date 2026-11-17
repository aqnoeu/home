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
    private boolean backgroundWaiting, backgroundSpeaking;
    private String pendingWakePhrase="";
    private final Runnable pendingWakeConfirmation=()->{
        if(!running || paused || backgroundWaiting || pendingWakePhrase.isEmpty())return;
        String phrase=pendingWakePhrase;
        pendingWakePhrase="";
        String command=activationSuffix(phrase,true);
        if(command!=null && SystemClock.elapsedRealtime()-lastWakeAt>=3500L){
            clearPartial();
            activate(command);
        }
    };
    private void rememberHypothesis(String hypothesis,boolean partial){
        getSharedPreferences("home",MODE_PRIVATE).edit()
            .putString("wake_last_hypothesis",hypothesis.length()>95?hypothesis.substring(0,95):hypothesis)
            .putString("wake_last_hypothesis_type",partial?"parcial":"final")
            .putLong("wake_last_hypothesis_at",System.currentTimeMillis()).apply();
    }
    private final Runnable visualHeartbeat=new Runnable(){
        @Override public void run(){
            if(!running)return;
            android.content.SharedPreferences p=getSharedPreferences("home",MODE_PRIVATE);
            String current=p.getString("wake_visual_state","desligado");
            if(!"desligado".equals(current))visualState(current);
            main.postDelayed(this,30000L);
        }
    };
    private String pendingCommand="";
    private final Runnable completePendingCommand=()->{
        if(!backgroundWaiting || paused || backgroundSpeaking)return;
        String command=pendingCommand.trim();
        if(command.isEmpty())return;
        pendingCommand="";
        replyBackground(command);
    };
    private final Runnable backgroundCommandTimeout=()->{
        if(backgroundWaiting && running && !paused){
            backgroundWaiting=false;
            pendingCommand="";
            main.removeCallbacks(completePendingCommand);
            visualState("armado");
            state("Nenhum comando ouvido. HOME voltou a aguardar Ei Home.");
        }
    };
    private boolean backgroundVoiceEnabled(){
        return getSharedPreferences("home",MODE_PRIVATE).getBoolean("wake_background_audio",false)
            && FaberOffline.isInstalled(this);
    }
    private void resetBackgroundState(){
        backgroundWaiting=false;
        backgroundSpeaking=false;
        pendingCommand="";
        main.removeCallbacks(backgroundCommandTimeout);
        main.removeCallbacks(completePendingCommand);
    }
    /** Capture the speech after the wake phrase from final OR stable partial Vosk text. */
    private void captureBackgroundCommand(String utterance, boolean partial){
        if(!backgroundWaiting || paused)return;
        String trimmed=utterance.trim();
        String suffix=activationSuffix(trimmed,true);
        // The recognizer may repeat the wake phrase before it hears the command.
        String command=suffix==null?trimmed:suffix;
        if(command.isEmpty())return;
        pendingCommand=command;
        main.removeCallbacks(backgroundCommandTimeout);
        main.postDelayed(backgroundCommandTimeout,12000L);
        main.removeCallbacks(completePendingCommand);
        // A final hypothesis is authoritative; partial words are confirmed after silence.
        main.postDelayed(completePendingCommand,partial?1400L:100L);
        state("Comando identificado: "+command.substring(0,Math.min(60,command.length())));
    }
    /** Tarefa curta com o detector já em execução. Não inicia outro microfone nem abre Activity. */
    private void beginBackgroundConversation(String initialCommand){
        String cmd=initialCommand==null?"":initialCommand.trim();
        backgroundWaiting=true;
        pendingCommand="";
        visualState("aguardando_comando");
        state("HOME chamado em segundo plano. Aguardando comando por voz.");
        main.removeCallbacks(backgroundCommandTimeout);
        main.postDelayed(backgroundCommandTimeout,12000L);
        // Wake detection may come from a partial Vosk hypothesis. Do not cut
        // off the rest of a sentence by closing the mic immediately.
        if(!cmd.isEmpty())captureBackgroundCommand(cmd,true);
    }
    private String offlineAnswer(String question){
        return HomeOfflineReplies.answer(this,question);
    }
    private void notifyBackgroundAnswer(String command,String answer){
        NotificationManager manager=getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel(
            "home_voice_response_v1","HOME — Respostas por voz",NotificationManager.IMPORTANCE_DEFAULT));
        Intent app=new Intent(this,MainActivity.class)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent tap=PendingIntent.getActivity(this,75,app,
            PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification notification=new Notification.Builder(this,"home_voice_response_v1")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("HOME: "+answer.substring(0,Math.min(48,answer.length())))
            .setContentText("Você: "+command)
            .setStyle(new Notification.BigTextStyle().bigText("Você: "+command+"\nHOME: "+answer))
            .setContentIntent(tap).setAutoCancel(true).build();
        manager.notify(75,notification);
    }
    private void resumeBackgroundListening(){
        backgroundSpeaking=false;
        if(running && enabled(this)){
            paused=false;
            visualState("armado");
            consecutiveAudioErrors=0;
            main.postDelayed(()->{
                if(running && !paused){
                    state("HOME voltou a ouvir Ei Home, Ok Home ou Home.");
                    beginListening();
                }
            },1100L);
        }
    }
    private void replyBackground(String command){
        if(!running || paused || backgroundSpeaking)return;
        backgroundWaiting=false;
        pendingCommand="";
        main.removeCallbacks(completePendingCommand);
        main.removeCallbacks(backgroundCommandTimeout);
        backgroundSpeaking=true;
        paused=true;
        visualState("falando");
        closeAudio(); // libera o AudioRecord antes da resposta local
        String answer=offlineAnswer(command);
        boolean saved=false;
        try{
            HomeChatStore store=HomeChatStore.get(this);
            String session=store.ensureActive();
            store.addTo(session,"user",command);
            store.addTo(session,"assistant",answer);
            saved=true;
        }catch(Exception ex){
            state("Falha ao salvar o comando: "+ex.getClass().getSimpleName());
        }
        getSharedPreferences("home",MODE_PRIVATE).edit().putString("wake_last_command",command).apply();
        if(!saved){
            resumeBackgroundListening();
            return;
        }
        // Notify only after the actual command and response have been saved.
        notifyBackgroundAnswer(command,answer);
        if(!backgroundVoiceEnabled()){
            state("Comando e resposta salvos. Resposta falada em segundo plano desativada.");
            resumeBackgroundListening();
            return;
        }
        state("Respondendo em segundo plano com a Faber.");
        boolean started=FaberOffline.speakBackground(this,answer,
            ()->main.post(this::resumeBackgroundListening));
        if(!started){
            state("Faber não iniciou. Resposta preservada no histórico.");
            resumeBackgroundListening();
        }
    }
    private final Runnable pendingNotificationRecovery=()->{
        if(running && paused && !MainActivity.isInForeground()){
            paused=false;
            visualState("armado");
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
            visualState(intent.getBooleanExtra("command_listening",false)?"aguardando_comando":"pausado");
            closeAudio();
            state("Detecção pausada durante a conversa.");
            if(running)return START_NOT_STICKY;
        }
        if(intent!=null && RESUME.equals(intent.getAction()) && running){
            if(backgroundSpeaking)return START_NOT_STICKY;
            resetBackgroundState();
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
                @Override public void onResult(String text){main.post(()->{if(generation==audioGeneration)detect(text,false);});}
                @Override public void onPartialResult(String text){main.post(()->{if(generation==audioGeneration)detect(text,true);});}
                @Override public void onFinalResult(String text){main.post(()->{if(generation==audioGeneration)detect(text,false);});}
                @Override public void onError(Exception e){main.post(()->{if(generation==audioGeneration)WakeWordService.this.onError(e);});}
                @Override public void onTimeout(){main.post(()->{if(generation==audioGeneration)WakeWordService.this.onTimeout();});}
            };
            if(!audio.startListening(sessionListener))throw new IllegalStateException("Não foi possível iniciar a escuta.");
            visualState("armado");
            state("Detector offline ouvindo. Diga Ei Home, Ok Home ou Home.");
        }catch(Exception ex){
            state("Falha no microfone offline: "+ex.getClass().getSimpleName());
            closeAudio();stopSelf();
        }
    }
    private void closeAudio(){
        clearPartial();
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
            "ok romi","ok rome","o que home","home ok home","home ei home","home","home home",
            "ei homem","oi homem","ok homem","ei rhome","ok rhome","ei rom","ok rom",
            "o que rome","oque home","okay home","ok roume"};
        for(String value:prefix){
            if(value.equals("home") && !finalOnly)continue; // "Home" isolado exige resultado final
            if(text.equals(value))return "";
            if(text.startsWith(value+" "))return text.substring(value.length()).trim();
        }
        // Variantes que o Vosk pt-BR produz para "ok home" (oquei, o k, rome, homem...).
        String heard=WakePhrases.suffix(text);
        if(heard==null && finalOnly)heard=WakePhrases.bareSuffix(text);
        return heard;
    }
    private void clearPartial(){
        partialCandidate="";
        partialCount=0;
        partialSince=0;
        pendingWakePhrase="";
        main.removeCallbacks(pendingWakeConfirmation);
    }
    private void detect(String hypothesis,boolean partial){
        if(!running || paused || hypothesis==null)return;
        String text;
        try{text=normalize(new JSONObject(hypothesis).optString(partial?"partial":"text",""));}
        catch(Exception ignored){return;}
        if(text.isEmpty())return;
        rememberHypothesis(text,partial);
        if(backgroundWaiting){
            captureBackgroundCommand(text,partial);
            return;
        }
        String suffix=activationSuffix(text,!partial);
        if(suffix==null)suffix=VoiceEnrollment.aliasSuffix(this,text,!partial);
        if(suffix==null){
            clearPartial();
            return;
        }
        long now=SystemClock.elapsedRealtime();
        if(now-lastWakeAt<3500L)return;
        if(!partial){
            clearPartial();
            activate(suffix);
            return;
        }
        // A short wake phrase may produce only a single partial and no timely final result.
        // A later unrelated hypothesis cancels the confirmation.
        if(text.equals(pendingWakePhrase))return;
        pendingWakePhrase=text;
        main.removeCallbacks(pendingWakeConfirmation);
        main.postDelayed(pendingWakeConfirmation,750L);
    }
    /** Sem a resposta falada em segundo plano, quem chama o HOME espera ver a conversa abrir.
     *  Com a permissão de sobreposição (já exigida pelo Notch) o Android permite abrir a tela. */
    private boolean canOpenChatFromBackground(){
        return !backgroundVoiceEnabled() && android.provider.Settings.canDrawOverlays(this);
    }
    private void postWakeNotification(Intent open){
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
    }
    private void activate(String command){
        lastWakeAt=SystemClock.elapsedRealtime();
        getSharedPreferences("home",MODE_PRIVATE).edit()
            .putLong("wake_last_recognized",System.currentTimeMillis()).apply();
        if(!MainActivity.isInForeground()){
            // Resposta falada em segundo plano ligada (opt-in): captura o comando sem abrir a tela.
            if(!canOpenChatFromBackground()){
                beginBackgroundConversation(command);
                return;
            }
        }
        paused=true;
        visualState("pausado");
        closeAudio(); // libera o AudioRecord ANTES do microfone de conversa
        Intent open=new Intent(this,MainActivity.class)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP)
            .putExtra(EXTRA_QUERY,command);
        boolean foreground=MainActivity.isInForeground();
        boolean blocked=false;
        try{
            state("Ativação reconhecida. Abrindo a conversa.");
            startActivity(open);
            if(foreground)return;
        }catch(RuntimeException ex){
            blocked=true;
            state("Reconhecido, mas o Android impediu a abertura automática.");
        }
        // O Android pode bloquear a abertura em segundo plano (às vezes sem avisar).
        // A notificação de alta prioridade é o plano B: imediata se houve erro, senão só
        // aparece se a conversa não tiver aberto em poucos segundos.
        if(blocked){
            state("Home reconheceu a frase. Toque na notificação para conversar.");
            postWakeNotification(open);
        }else{
            main.postDelayed(()->{
                if(running && !MainActivity.isInForeground()){
                    state("Home reconheceu a frase. Toque na notificação para conversar.");
                    postWakeNotification(open);
                }
            },2500L);
        }
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
        visualState("desligado");
        closeAudio();
        if(model!=null){try{model.close();}catch(Exception ignored){}model=null;}
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent){return null;}
}
