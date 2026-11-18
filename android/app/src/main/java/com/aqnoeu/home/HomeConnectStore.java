package com.aqnoeu.home;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import org.json.JSONArray;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Local API profiles. Secrets stay encrypted at rest, never included in LLM prompts. */
public final class HomeConnectStore {
    private static final String PREF = "home_connect_profiles";
    private static final String ALIAS = "home_connect_profiles_aes_v1";
    private HomeConnectStore(){}

    private static SecretKey secret() throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);
        if(store.containsAlias(ALIAS))
            return ((KeyStore.SecretKeyEntry)store.getEntry(ALIAS,null)).getSecretKey();
        KeyGenerator generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
        generator.init(new KeyGenParameterSpec.Builder(ALIAS,
            KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256).build());
        return generator.generateKey();
    }
    private static JSONArray load(Context context) throws Exception {
        SharedPreferences p=context.getSharedPreferences(PREF,Context.MODE_PRIVATE);
        String raw=p.getString("payload",null),iv=p.getString("iv",null);
        if(raw==null||iv==null)return new JSONArray();
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE,secret(),
            new GCMParameterSpec(128,Base64.decode(iv,Base64.NO_WRAP)));
        return new JSONArray(new String(cipher.doFinal(
            Base64.decode(raw,Base64.NO_WRAP)),StandardCharsets.UTF_8));
    }
    private static void save(Context context,JSONArray profiles) throws Exception {
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE,secret());
        byte[] encrypted=cipher.doFinal(profiles.toString().getBytes(StandardCharsets.UTF_8));
        boolean ok=context.getSharedPreferences(PREF,Context.MODE_PRIVATE).edit()
            .putString("payload",Base64.encodeToString(encrypted,Base64.NO_WRAP))
            .putString("iv",Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP))
            .commit();
        if(!ok)throw new IllegalStateException("Falha ao salvar a conexão.");
    }
    public static JSONArray profiles(Context context) throws Exception {
        JSONArray stored=load(context),publicList=new JSONArray();
        for(int i=0;i<stored.length();i++){
            JSONObject entry=stored.getJSONObject(i);
            publicList.put(new JSONObject()
                .put("name",entry.optString("name"))
                .put("url",entry.optString("url"))
                .put("hasKey",!entry.optString("key").isEmpty()));
        }
        return publicList;
    }
    public static void add(Context context,String name,String url,String apiKey) throws Exception {
        String n=name==null?"":name.trim(),u=url==null?"":url.trim();
        if(n.isEmpty()||n.length()>50)throw new IllegalArgumentException("Informe um nome de até 50 caracteres.");
        if(u.length()>300)throw new IllegalArgumentException("Endereço muito longo.");
        java.net.URI target=new java.net.URI(u);
        if(!"https".equalsIgnoreCase(target.getScheme())
            ||target.getHost()==null ||target.getUserInfo()!=null
            ||target.getFragment()!=null ||target.getPort()!=-1)
            throw new IllegalArgumentException("Informe uma URL HTTPS válida, sem porta personalizada.");
        JSONArray entries=load(context);
        if(entries.length()>=12)throw new IllegalArgumentException("Limite de 12 conexões.");
        for(int i=0;i<entries.length();i++)
            if(n.equalsIgnoreCase(entries.getJSONObject(i).optString("name")))
                throw new IllegalArgumentException("Já existe uma conexão com esse nome.");
        entries.put(new JSONObject().put("name",n).put("url",u)
            .put("key",apiKey==null?"":apiKey.trim()));
        save(context,entries);
    }
    /** Internal use only: never return this object to the model or UI. */
    static JSONObject privateProfile(Context context,String name) throws Exception {
        JSONArray entries=load(context);
        for(int i=0;i<entries.length();i++){
            JSONObject item=entries.getJSONObject(i);
            if(name.equals(item.optString("name")))return item;
        }
        return null;
    }
    public static void remove(Context context,String name) throws Exception {
        JSONArray entries=load(context),updated=new JSONArray();
        for(int i=0;i<entries.length();i++){
            JSONObject item=entries.getJSONObject(i);
            if(!name.equals(item.optString("name")))updated.put(item);
        }
        save(context,updated);
    }
}
