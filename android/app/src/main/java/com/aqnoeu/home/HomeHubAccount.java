package com.aqnoeu.home;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import org.json.JSONArray;
import org.json.JSONObject;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.UUID;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** HOME account — Supabase credentials from Home Hub; local functions remain offline.
 * Network methods must be called from background threads, never the UI thread.
 */
public final class HomeHubAccount {
    private static final String HUB="https://homehub-ia.vercel.app";
    private static final String KEY_ALIAS="home_hub_refresh_v1";
    private static final String PREFS="home_hub_account";
    private final Context app;
    private final SharedPreferences storage;
    private String endpoint,publicKey,access,userId,email;
    public HomeHubAccount(Context context){
        app=context.getApplicationContext();
        storage=app.getSharedPreferences(PREFS,Context.MODE_PRIVATE);
    }
    private JSONObject http(String url,String method,JSONObject body,String bearer,String apiKey)throws Exception{
        HttpURLConnection con=(HttpURLConnection)new URL(url).openConnection();
        con.setConnectTimeout(10000);con.setReadTimeout(20000);
        con.setRequestMethod(method);
        con.setRequestProperty("Accept","application/json");
        if(apiKey!=null)con.setRequestProperty("apikey",apiKey);
        if(bearer!=null)con.setRequestProperty("Authorization","Bearer "+bearer);
        if(body!=null){
            con.setDoOutput(true);con.setRequestProperty("Content-Type","application/json");
            byte[] data=body.toString().getBytes(StandardCharsets.UTF_8);
            try(OutputStream out=con.getOutputStream()){out.write(data);}
        }
        int status=con.getResponseCode();
        InputStream stream=status>=400?con.getErrorStream():con.getInputStream();
        ByteArrayOutputStream buffer=new ByteArrayOutputStream();
        if(stream!=null){try(InputStream s=stream){byte[] b=new byte[4096];int n;while((n=s.read(b))>=0)buffer.write(b,0,n);}}
        String raw=buffer.toString("UTF-8");
        if(status>=400){String error=raw;try{JSONObject o=new JSONObject(raw);error=o.optString("error_description",o.optString("message",o.optString("error",raw)));}catch(Exception ignored){}throw new IllegalStateException("HTTP "+status+": "+error);}
        return raw.startsWith("[")?new JSONObject().put("rows",new JSONArray(raw)):raw.isEmpty()?new JSONObject():new JSONObject(raw);
    }
    private void config()throws Exception{
        if(endpoint!=null)return;
        JSONObject c=http(HUB+"/api/config","GET",null,null,null);
        endpoint=c.getString("supabaseUrl");publicKey=c.getString("supabasePublishableKey");
    }
    private void secureStore(String refresh)throws Exception{
        KeyStore ks=KeyStore.getInstance("AndroidKeyStore");ks.load(null);
        if(!ks.containsAlias(KEY_ALIAS)){
            KeyGenerator gen=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
            gen.init(new KeyGenParameterSpec.Builder(KEY_ALIAS,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());
            gen.generateKey();
        }
        SecretKey key=(SecretKey)ks.getKey(KEY_ALIAS,null);
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key);
        storage.edit().putString("refresh",Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP)+":"+
            Base64.encodeToString(cipher.doFinal(refresh.getBytes(StandardCharsets.UTF_8)),Base64.NO_WRAP)).apply();
    }
    private String secureRead()throws Exception{
        String packed=storage.getString("refresh","");
        if(packed.isEmpty())return null;
        String[] parts=packed.split(":",2);if(parts.length!=2)return null;
        KeyStore ks=KeyStore.getInstance("AndroidKeyStore");ks.load(null);
        SecretKey key=(SecretKey)ks.getKey(KEY_ALIAS,null);if(key==null)return null;
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE,key,new GCMParameterSpec(128,Base64.decode(parts[0],Base64.NO_WRAP)));
        return new String(cipher.doFinal(Base64.decode(parts[1],Base64.NO_WRAP)),StandardCharsets.UTF_8);
    }
    private void accept(JSONObject session)throws Exception{
        access=session.getString("access_token");
        JSONObject u=session.getJSONObject("user");userId=u.getString("id");email=u.optString("email");
        secureStore(session.getString("refresh_token"));
        register();
    }
    public synchronized void signIn(String login,String password)throws Exception{
        config();
        accept(http(endpoint+"/auth/v1/token?grant_type=password","POST",
            new JSONObject().put("email",login).put("password",password),null,publicKey));
    }
    public synchronized boolean resume()throws Exception{
        config();String refresh=secureRead();
        if(refresh==null)return false;
        try{
            accept(http(endpoint+"/auth/v1/token?grant_type=refresh_token","POST",
                new JSONObject().put("refresh_token",refresh),null,publicKey));return true;
        }catch(Exception e){storage.edit().remove("refresh").apply();throw e;}
    }
    public synchronized void signOut(){
        if(access!=null)try{http(endpoint+"/auth/v1/logout","POST",new JSONObject(),access,publicKey);}catch(Exception ignored){}
        access=null;userId=null;email=null;storage.edit().remove("refresh").apply();
    }
    public boolean connected(){return access!=null&&userId!=null;}
    public String email(){return email;}
    private void register()throws Exception{
        String client=storage.getString("client_id",null);
        if(client==null){client=UUID.randomUUID().toString();storage.edit().putString("client_id",client).apply();}
        JSONObject device=new JSONObject().put("user_id",userId).put("client_id",client).put("platform","android")
            .put("display_name",android.os.Build.MANUFACTURER+" "+android.os.Build.MODEL);
        // Upsert with one account-scoped client ID, preserving independent device records.
        postRest("home_devices?on_conflict=user_id,client_id",device,true);
    }
    private JSONObject postRest(String path,Object body,boolean upsert)throws Exception{
        HttpURLConnection con=(HttpURLConnection)new URL(endpoint+"/rest/v1/"+path).openConnection();
        con.setRequestMethod("POST");con.setConnectTimeout(10000);con.setReadTimeout(15000);
        con.setRequestProperty("apikey",publicKey);con.setRequestProperty("Authorization","Bearer "+access);
        con.setRequestProperty("Content-Type","application/json");
        if(upsert)con.setRequestProperty("Prefer",path.startsWith("homehub_messages")?"resolution=ignore-duplicates":"resolution=merge-duplicates");
        con.setDoOutput(true);try(OutputStream out=con.getOutputStream()){out.write(body.toString().getBytes(StandardCharsets.UTF_8));}
        int code=con.getResponseCode();if(code>=400)throw new IllegalStateException("Falha de sincronização: HTTP "+code);
        con.disconnect();return new JSONObject();
    }
    public synchronized JSONObject preferences()throws Exception{
        if(!connected())return new JSONObject();
        JSONObject r=http(endpoint+"/rest/v1/home_preferences?select=*&user_id=eq."+userId,"GET",null,access,publicKey);
        JSONArray rows=r.optJSONArray("rows");return rows!=null&&rows.length()>0?rows.getJSONObject(0):new JSONObject();
    }
    public synchronized void savePreferences(String model,String style,boolean chats,boolean emotions)throws Exception{
        if(!connected())throw new IllegalStateException("Faça login primeiro.");
        postRest("home_preferences?on_conflict=user_id",new JSONObject()
            .put("user_id",userId).put("preferred_model",model)
            .put("response_style",style).put("sync_chats",chats)
            .put("sync_emotions",emotions),true);
    }
    /** Sync only after a deliberate opt-in. Raw microphone audio never uploads. */
    public synchronized void uploadVoiceProfile(JSONObject local)throws Exception{
        if(!connected())throw new IllegalStateException("Entre na Conta HOME.");
        JSONObject stored=voiceProfile();
        if(!stored.optBoolean("sync_enabled",false))
            throw new IllegalStateException("Autorize primeiro a sincronização do perfil de voz na Conta HOME.");
        JSONObject settings=stored.optJSONObject("settings");
        if(settings==null)settings=new JSONObject();
        settings.put("android",local);
        postRest("home_voice_profiles?on_conflict=user_id",new JSONObject()
            .put("user_id",userId).put("sync_enabled",true)
            .put("settings",settings).put("reviewed_aliases",new JSONObject())
            .put("updated_at",new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX",
                java.util.Locale.US).format(new java.util.Date())),true);
    }
    public synchronized JSONObject voiceProfile()throws Exception{
        if(!connected())throw new IllegalStateException("Entre na Conta HOME.");
        JSONObject r=http(endpoint+"/rest/v1/home_voice_profiles?select=*&user_id=eq."+userId,
            "GET",null,access,publicKey);
        JSONArray rows=r.optJSONArray("rows");
        return rows!=null&&rows.length()>0?rows.getJSONObject(0):new JSONObject();
    }
    public synchronized void authorizeVoiceSync()throws Exception{
        if(!connected())throw new IllegalStateException("Entre na Conta HOME.");
        JSONObject current=voiceProfile();
        postRest("home_voice_profiles?on_conflict=user_id",new JSONObject()
            .put("user_id",userId).put("sync_enabled",true)
            .put("settings",current.optJSONObject("settings")==null?new JSONObject():current.getJSONObject("settings"))
            .put("reviewed_aliases",current.optJSONObject("reviewed_aliases")==null?new JSONObject():current.getJSONObject("reviewed_aliases")),true);
    }
    public synchronized JSONObject downloadVoiceProfile()throws Exception{
        JSONObject record=voiceProfile();
        if(!record.optBoolean("sync_enabled",false))
            throw new IllegalStateException("A sincronização de voz ainda não foi autorizada.");
        JSONObject byPlatform=record.optJSONObject("settings");
        if(byPlatform==null)return new JSONObject();
        return byPlatform.optJSONObject("android")==null?new JSONObject():byPlatform.getJSONObject("android");
    }
    public synchronized JSONArray cloudChats()throws Exception{
        if(!connected())return new JSONArray();
        return http(endpoint+"/rest/v1/homehub_chats?select=id,title,updated_at&order=updated_at.desc&limit=40",
            "GET",null,access,publicKey).optJSONArray("rows");
    }
    public synchronized JSONArray cloudMessages(String chatId)throws Exception{
        if(!connected())return new JSONArray();
        return http(endpoint+"/rest/v1/homehub_messages?select=role,content,created_at&chat_id=eq."+
            java.net.URLEncoder.encode(chatId,"UTF-8")+"&order=created_at.asc&limit=100",
            "GET",null,access,publicKey).optJSONArray("rows");
    }
    /** Upload on explicit user request. Deterministic message IDs make retries idempotent. */
    public synchronized int uploadLocalChats(HomeChatStore local)throws Exception{
        if(!connected())throw new IllegalStateException("Entre na conta HOME.");
        if(!preferences().optBoolean("sync_chats",false))
            throw new IllegalStateException("Ative e salve a sincronização de conversas antes de enviar seu histórico.");
        java.util.List<JSONObject> conversations=local.conversations();
        JSONArray chats=new JSONArray(),messages=new JSONArray();
        int count=0;
        for(JSONObject c:conversations){
            String id=c.optString("id");
            try{UUID.fromString(id);}catch(Exception ignored){continue;}
            chats.put(new JSONObject().put("id",id).put("user_id",userId)
                .put("title",c.optString("title","Conversa").substring(0,
                    Math.min(120,c.optString("title","Conversa").length()))).put("model","auto"));
            JSONArray items=c.optJSONArray("messages");
            if(items==null)continue;
            for(int i=0;i<items.length();i++){
                JSONObject m=items.optJSONObject(i);
                if(m==null)continue;
                String role=m.optString("role");
                if(!"user".equals(role)&&!"assistant".equals(role))continue;
                String content=m.optString("text","").trim();
                if(content.isEmpty())continue;
                String mid=UUID.nameUUIDFromBytes(("home-mobile:"+id+":"+i).getBytes(StandardCharsets.UTF_8)).toString();
                messages.put(new JSONObject().put("id",mid).put("chat_id",id).put("user_id",userId)
                    .put("role",role).put("content",content));
                count++;
            }
        }
        if(chats.length()>0)postRest("homehub_chats?on_conflict=id",chats,true);
        // Chunking avoids oversized Data API requests on phones with long histories.
        for(int start=0;start<messages.length();start+=80){
            JSONArray batch=new JSONArray();
            for(int i=start;i<Math.min(messages.length(),start+80);i++)batch.put(messages.get(i));
            postRest("homehub_messages?on_conflict=id",batch,true);
        }
        return count;
    }

}
