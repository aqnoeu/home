package com.aqnoeu.home;

import android.content.Context;
import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Private on-device persistent HOME chat history.
 * No voice recordings or API keys are stored, only displayed text.
 * Reads/writes are synchronized; atomic file commits prevent half-written JSON.
 */
public final class HomeChatStore {
    private static final String FILE="home_conversations_v1.json";
    private static final int MAX_CONVERSATIONS=100;
    private static final int MAX_MESSAGES=250;
    private static final int MAX_TEXT=1200;
    private static HomeChatStore instance;
    private final AtomicFile disk;
    private JSONObject state;
    private HomeChatStore(Context context){
        disk=new AtomicFile(new File(context.getFilesDir(),FILE));
        try {
            byte[] bytes=disk.readFully();
            state=new JSONObject(new String(bytes,StandardCharsets.UTF_8));
            if(!state.has("chats"))throw new IllegalArgumentException();
        }catch(Exception ignored){
            state=new JSONObject();
            try{
                state.put("active","");
                state.put("chats",new JSONArray());
            }catch(Exception impossible){}
        }
    }
    public static synchronized HomeChatStore get(Context context){
        if(instance==null)instance=new HomeChatStore(context.getApplicationContext());
        return instance;
    }
    private JSONArray chats(){return state.optJSONArray("chats");}
    private JSONObject find(String id){
        if(id==null)return null;
        JSONArray a=chats();
        for(int i=0;i<a.length();i++){
            JSONObject c=a.optJSONObject(i);
            if(c!=null&&id.equals(c.optString("id")))return c;
        }
        return null;
    }
    private void flush(){
        FileOutputStream output=null;
        try{
            output=disk.startWrite();
            output.write(state.toString().getBytes(StandardCharsets.UTF_8));
            disk.finishWrite(output);
        }catch(Exception e){
            if(output!=null)disk.failWrite(output);
            throw new IllegalStateException("Não foi possível salvar o histórico.",e);
        }
    }
    public synchronized String activeId(){return state.optString("active","");}
    public synchronized String newChat(){
        String id=UUID.randomUUID().toString();
        JSONObject chat=new JSONObject();
        try{
            chat.put("id",id);chat.put("title","Nova conversa");
            chat.put("created",System.currentTimeMillis());
            chat.put("updated",System.currentTimeMillis());
            chat.put("messages",new JSONArray());
            JSONArray a=chats();
            a.put(chat);
            if(a.length()>MAX_CONVERSATIONS){
                JSONArray trimmed=new JSONArray();
                for(int i=a.length()-MAX_CONVERSATIONS;i<a.length();i++)
                    trimmed.put(a.getJSONObject(i));
                state.put("chats",trimmed);
            }
            state.put("active",id);flush();return id;
        }catch(Exception e){throw new IllegalStateException(e);}
    }
    public synchronized String ensureActive(){
        String id=activeId();
        return find(id)!=null?id:newChat();
    }
    public synchronized void select(String id){
        if(find(id)==null)throw new IllegalArgumentException("Conversa não encontrada.");
        try{state.put("active",id);flush();}
        catch(Exception e){throw new IllegalStateException(e);}
    }
    public synchronized void delete(String id){
        JSONArray kept=new JSONArray();
        JSONArray a=chats();
        for(int i=0;i<a.length();i++){
            JSONObject c=a.optJSONObject(i);
            if(c!=null&&!id.equals(c.optString("id")))kept.put(c);
        }
        try{
            state.put("chats",kept);
            if(id.equals(activeId()))state.put("active","");
            flush();
        }catch(Exception e){throw new IllegalStateException(e);}
    }
    public synchronized void add(String role,String text){
        if(!"user".equals(role)&&!"assistant".equals(role))return;
        if(text==null||text.trim().isEmpty())return;
        String id=ensureActive();
        JSONObject chat=find(id);
        if(chat==null)return;
        try {
            JSONArray messages=chat.getJSONArray("messages");
            JSONObject message=new JSONObject()
                .put("role",role)
                .put("text",text.trim().substring(0,Math.min(MAX_TEXT,text.trim().length())))
                .put("time",System.currentTimeMillis());
            messages.put(message);
            if(messages.length()>MAX_MESSAGES){
                JSONArray trimmed=new JSONArray();
                for(int i=messages.length()-MAX_MESSAGES;i<messages.length();i++)
                    trimmed.put(messages.getJSONObject(i));
                chat.put("messages",trimmed);
            }
            if("user".equals(role)&&"Nova conversa".equals(chat.optString("title")))
                chat.put("title",text.trim().substring(0,Math.min(55,text.trim().length())));
            chat.put("updated",System.currentTimeMillis());
            flush();
        }catch(Exception e){throw new IllegalStateException(e);}
    }
    public synchronized JSONArray messages(){
        JSONObject c=find(activeId());
        if(c==null)return new JSONArray();
        return new JSONArray(c.optJSONArray("messages").toString());
    }
    public synchronized List<JSONObject> conversations(){
        List<JSONObject> result=new ArrayList<>();
        JSONArray a=chats();
        for(int i=a.length()-1;i>=0;i--){
            JSONObject c=a.optJSONObject(i);
            if(c!=null)result.add(c);
        }
        return result;
    }
    public synchronized JSONArray context(){
        JSONArray messages=messages(),history=new JSONArray();
        for(int i=Math.max(0,messages.length()-8);i<messages.length();i++){
            JSONObject m=messages.optJSONObject(i);
            if(m!=null){
                history.put(new JSONObject()
                    .put("role",m.optString("role"))
                    .put("content",m.optString("text")));
            }
        }
        return history;
    }
}
