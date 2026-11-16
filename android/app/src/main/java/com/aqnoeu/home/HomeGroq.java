package com.aqnoeu.home;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.concurrent.atomic.AtomicBoolean;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Direct HTTPS Groq client for the owner's own device.
 * Key is encrypted using non-exportable Android Keystore AES-GCM, not bundled in APK.
 * No proxy, Cloudflare or Android system TTS.
 */
public final class HomeGroq {
    private static final String API = "https://api.groq.com/openai/v1/chat/completions";
    private static final String MODEL = "openai/gpt-oss-20b";
    private static final String ALIAS = "home_groq_key_v1";
    private static final String PREF = "home_groq_private";
    private static final String SYSTEM = "Você é HOME (Helpful, Organized, Mindful & Efficient), assistente simpático e discreto. Responda em português brasileiro de forma clara, objetiva e natural para ser falada em voz alta. Prefira até duas frases, com no máximo 380 caracteres. Sem emojis, markdown ou listas na voz. Se não souber, admita. Você não executa ações no celular por conta própria.";
    private static final AtomicBoolean BUSY = new AtomicBoolean(false);
    private static final Object HISTORY_LOCK = new Object();
    private static final JSONArray HISTORY = new JSONArray();
    private HomeGroq() {}

    public interface Callback {
        void onAnswer(String answer);
        void onError(String explanation);
    }

    private static SecretKey secret() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        if(ks.containsAlias(ALIAS)) return ((KeyStore.SecretKeyEntry)ks.getEntry(ALIAS,null)).getSecretKey();
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
        generator.init(new KeyGenParameterSpec.Builder(ALIAS,
                KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256).build());
        return generator.generateKey();
    }
    private static void save(Context context,String value) throws Exception {
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE,secret());
        byte[] ciphertext=cipher.doFinal(value.getBytes(StandardCharsets.UTF_8));
        context.getSharedPreferences(PREF,Context.MODE_PRIVATE).edit()
            .putString("secret",Base64.encodeToString(ciphertext,Base64.NO_WRAP))
            .putString("iv",Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP))
            .apply();
    }
    private static String key(Context context) {
        try {
            SharedPreferences p=context.getSharedPreferences(PREF,Context.MODE_PRIVATE);
            String data=p.getString("secret",null), iv=p.getString("iv",null);
            if(data==null||iv==null)return null;
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE,secret(),
                new GCMParameterSpec(128,Base64.decode(iv,Base64.NO_WRAP)));
            return new String(cipher.doFinal(Base64.decode(data,Base64.NO_WRAP)),StandardCharsets.UTF_8);
        }catch(Exception e){return null;}
    }
    public static boolean connected(Context context){return key(context)!=null;}
    public static void disconnect(Context context){
        context.getSharedPreferences(PREF,Context.MODE_PRIVATE).edit().clear().apply();
        synchronized(HISTORY_LOCK){while(HISTORY.length()>0)HISTORY.remove(HISTORY.length()-1);}
    }
    /** Save a key supplied through HOME's inline, non-modal settings card. */
    public static void connect(Context context,String value) throws Exception {
        String normalized=value==null?"":value.trim();
        if(!normalized.startsWith("gsk_")||normalized.length()<25)
            throw new IllegalArgumentException("A chave Groq deve começar com gsk_.");
        save(context,normalized);
    }
    public static void ask(Activity activity,String question,Callback callback) {
        String apiKey=key(activity);
        if(apiKey==null){callback.onError("Conecte a Groq no Assistente uma única vez.");return;}
        String q=question==null?"":question.trim();
        if(q.isEmpty())return;
        if(q.length()>750){callback.onError("Pergunta muito longa (limite de 750 caracteres).");return;}
        if(!BUSY.compareAndSet(false,true)){callback.onError("O Home ainda está respondendo à pergunta anterior.");return;}
        new Thread(()->{
            String answer=null,error=null;
            HttpURLConnection connection=null;
            try {
                JSONArray messages=new JSONArray();
                messages.put(new JSONObject().put("role","system").put("content",SYSTEM));
                synchronized(HISTORY_LOCK){
                    int start=Math.max(0,HISTORY.length()-8);
                    for(int i=start;i<HISTORY.length();i++)messages.put(HISTORY.getJSONObject(i));
                }
                messages.put(new JSONObject().put("role","user").put("content",q));
                JSONObject body=new JSONObject().put("model",MODEL)
                    .put("messages",messages).put("temperature",0.5)
                    .put("max_completion_tokens",450).put("reasoning_effort","low")
                    .put("include_reasoning",false).put("stream",false);
                connection=(HttpURLConnection)new URL(API).openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(12000);connection.setReadTimeout(28000);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type","application/json");
                connection.setRequestProperty("Authorization","Bearer "+apiKey);
                try(OutputStream out=connection.getOutputStream()){
                    out.write(body.toString().getBytes(StandardCharsets.UTF_8));
                }
                int status=connection.getResponseCode();
                if(status==401||status==403)throw new IllegalStateException("Chave Groq recusada. Verifique a chave nas configurações.");
                if(status==429)throw new IllegalStateException("Limite de uso da Groq atingido. Tente novamente mais tarde.");
                if(status!=200)throw new IllegalStateException("Groq indisponível (HTTP "+status+").");
                ByteArrayOutputStream buffer=new ByteArrayOutputStream();
                try(InputStream stream=connection.getInputStream()){
                    byte[] chunk=new byte[4096];int n;
                    while((n=stream.read(chunk))!=-1){
                        if(buffer.size()+n>128000)throw new IllegalStateException("Resposta excedeu o limite.");
                        buffer.write(chunk,0,n);
                    }
                }
                JSONObject reply=new JSONObject(buffer.toString("UTF-8"));
                String content=reply.getJSONArray("choices").getJSONObject(0)
                    .getJSONObject("message").optString("content","").trim();
                if(content.isEmpty())throw new IllegalStateException("A Groq não retornou texto para falar.");
                answer=content.length()>850?content.substring(0,850):content;
                synchronized(HISTORY_LOCK){
                    HISTORY.put(new JSONObject().put("role","user").put("content",q));
                    HISTORY.put(new JSONObject().put("role","assistant").put("content",answer));
                    while(HISTORY.length()>10)HISTORY.remove(0);
                }
            }catch(Exception e){error=e.getMessage()==null?"Falha de conexão com Groq.":e.getMessage();}
            finally{if(connection!=null)connection.disconnect();BUSY.set(false);}
            final String result=answer,problem=error;
            activity.runOnUiThread(()->{
                if(activity.isFinishing())return;
                if(problem!=null)callback.onError(problem);else callback.onAnswer(result);
            });
        },"HomeGroq").start();
    }
}
