package com.aqnoeu.home;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import java.util.ArrayList;

/** In-app speech capture: no ACTION_RECOGNIZE_SPEECH activity or Google dialog. */
public final class HomeVoiceCapture implements RecognitionListener {
    public interface Callback {
        void onPartial(String phrase);
        void onFinal(String phrase);
        void onFailure(String reason);
    }
    private final MainActivity activity;
    private final Callback callback;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private SpeechRecognizer recognizer;
    private boolean done=false;

    public HomeVoiceCapture(MainActivity activity,Callback callback) {
        this.activity=activity;
        this.callback=callback;
    }
    public boolean start(){
        if(!SpeechRecognizer.isRecognitionAvailable(activity)){
            callback.onFailure("O Android não disponibilizou reconhecimento de fala.");
            return false;
        }
        try{
            recognizer=SpeechRecognizer.createSpeechRecognizer(activity);
            recognizer.setRecognitionListener(this);
            Intent request=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
            request.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
            request.putExtra(RecognizerIntent.EXTRA_LANGUAGE,"pt-BR");
            request.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,true);
            request.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS,1);
            request.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE,true);
            recognizer.startListening(request);
            return true;
        }catch(Exception ex){
            release();
            callback.onFailure("Não foi possível iniciar o microfone: "+ex.getMessage());
            return false;
        }
    }
    public void release(){
        done=true;
        SpeechRecognizer old=recognizer;
        recognizer=null;
        if(old!=null){
            try{old.cancel();}catch(Exception ignored){}
            try{old.destroy();}catch(Exception ignored){}
        }
    }
    private String first(Bundle data){
        if(data==null)return "";
        ArrayList<String> items=data.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        return items==null||items.isEmpty()?"":items.get(0).trim();
    }
    @Override public void onReadyForSpeech(Bundle data){}
    @Override public void onBeginningOfSpeech(){}
    @Override public void onRmsChanged(float rms){}
    @Override public void onBufferReceived(byte[] buffer){}
    @Override public void onEndOfSpeech(){}
    @Override public void onError(int error){
        if(done)return;
        done=true;
        callback.onFailure(error==SpeechRecognizer.ERROR_NO_MATCH||error==SpeechRecognizer.ERROR_SPEECH_TIMEOUT?
            "Não ouvi uma frase. Toque no microfone para tentar novamente.":
            "Falha no reconhecimento de voz (código "+error+").");
    }
    @Override public void onResults(Bundle results){
        if(done)return;
        done=true;
        String phrase=first(results);
        if(phrase.isEmpty())callback.onFailure("Não reconheci nenhuma frase.");
        else callback.onFinal(phrase);
    }
    @Override public void onPartialResults(Bundle partialResults){
        if(!done){String phrase=first(partialResults);if(!phrase.isEmpty())callback.onPartial(phrase);}
    }
    @Override public void onEvent(int eventType,Bundle params){}
}