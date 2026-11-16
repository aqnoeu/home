package com.aqnoeu.home;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.text.InputType;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import org.json.JSONObject;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

/** User-configured secured proxy; never embeds a provider's secret in the APK. */
public final class HomeAi {
    private HomeAi() {}
    public static void configure(Activity activity) {
        SharedPreferences p=activity.getSharedPreferences("home_ai",Context.MODE_PRIVATE);
        LinearLayout fields=new LinearLayout(activity);
        fields.setOrientation(LinearLayout.VERTICAL);
        fields.setPadding(28,12,28,0);
        TextView info=new TextView(activity);
        info.setText("Configure um servidor HTTPS do Home com autenticação. Não cole sua chave Groq aqui. As mensagens serão enviadas somente quando você conversar.");
        fields.addView(info);
        EditText endpoint=new EditText(activity);
        endpoint.setHint("https://seu-servidor/ai");
        endpoint.setSingleLine(true);
        endpoint.setText(p.getString("endpoint","https://home-ai.aqnoeu-home.workers.dev/ai"));
        fields.addView(endpoint);
        EditText token=new EditText(activity);
        token.setHint("Código de acesso do seu servidor");
        token.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        token.setSingleLine(true);
        token.setText(p.getString("token",""));
        fields.addView(token);
        new AlertDialog.Builder(activity).setTitle("Home — conexão segura com IA")
            .setView(fields).setPositiveButton("Salvar",(d,w)->{
                String url=endpoint.getText().toString().trim();
                if (!url.isEmpty() && (!url.startsWith("https://") || url.contains("@"))) {
                    new AlertDialog.Builder(activity).setMessage("Use um endpoint HTTPS válido, sem usuário ou senha na URL.")
                        .setPositiveButton("OK",null).show();
                    return;
                }
                p.edit().putString("endpoint",url).putString("token",token.getText().toString().trim()).apply();
            }).setNeutralButton("Desconectar",(d,w)->p.edit().clear().apply())
            .setNegativeButton("Cancelar",null).show();
    }
    public static void chat(Activity activity) {
        SharedPreferences p=activity.getSharedPreferences("home_ai",Context.MODE_PRIVATE);
        String endpoint=p.getString("endpoint","");
        String token=p.getString("token","");
        if (endpoint.isEmpty() || token.isEmpty()) {
            new AlertDialog.Builder(activity).setTitle("Home")
                .setMessage("Por enquanto posso reagir localmente. Para conversar usando IA, configure primeiro o servidor seguro do Home — sem colocar a chave Groq no aplicativo.")
                .setPositiveButton("Configurar", (d,w)->configure(activity))
                .setNegativeButton("Fechar",null).show();
            return;
        }
        EditText entry=new EditText(activity);
        entry.setHint("Fale com o Home...");
        entry.setMaxLines(4);
        LinearLayout content=new LinearLayout(activity);
        content.setPadding(26,12,26,0);
        content.addView(entry);
        new AlertDialog.Builder(activity).setTitle("Conversar com Home").setView(content)
            .setPositiveButton("Enviar",(d,w)->{
                String question=entry.getText().toString().trim();
                if(question.isEmpty())return;
                if(question.length()>500) {
                    show(activity,"Sua mensagem pode ter no máximo 500 caracteres.");return;
                }
                new Thread(()->{
                    String answer;
                    int newMood=0;
                    try {
                        URL url=new URL(endpoint);
                        if(!"https".equalsIgnoreCase(url.getProtocol()))throw new Exception("Somente HTTPS");
                        HttpURLConnection conn=(HttpURLConnection)url.openConnection();
                        conn.setRequestMethod("POST");
                        conn.setConnectTimeout(12000);
                        conn.setReadTimeout(25000);
                        conn.setRequestProperty("Authorization","Bearer "+token);
                        conn.setRequestProperty("Content-Type","application/json; charset=utf-8");
                        conn.setDoOutput(true);
                        JSONObject body=new JSONObject();
                        body.put("message",question);
                        body.put("mood",activity.getSharedPreferences("home",Context.MODE_PRIVATE).getInt("mood",0));
                        try(OutputStream out=conn.getOutputStream()){
                            out.write(body.toString().getBytes(StandardCharsets.UTF_8));
                        }
                        if(conn.getResponseCode()!=200)throw new Exception("Servidor respondeu HTTP "+conn.getResponseCode());
                        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
                        try(InputStream in=conn.getInputStream()){
                            byte[] block=new byte[4096]; int n;
                            while((n=in.read(block))!=-1){
                                if(bytes.size()+n>12000)throw new Exception("Resposta muito longa");
                                bytes.write(block,0,n);
                            }
                        } finally {conn.disconnect();}
                        JSONObject result=new JSONObject(bytes.toString("UTF-8"));
                        answer=result.optString("reply","Sem resposta.");
                        newMood=Math.max(0,Math.min(3,result.optInt("mood",0)));
                    } catch(Exception ex){answer="Não consegui falar com a IA: "+ex.getMessage();}
                    final int mood=newMood;
                    final String reply=answer;
                    activity.runOnUiThread(()->{
                        activity.getSharedPreferences("home",Context.MODE_PRIVATE).edit().putInt("mood",mood).apply();
                        try {activity.startService(new android.content.Intent(activity,OverlayService.class));}
                        catch(Exception ignored){}
                        show(activity,reply);
                    });
                }).start();
            }).setNegativeButton("Cancelar",null).show();
    }
    /** Push-to-talk can use the same authenticated backend as the text chat. */
    public static boolean voiceReply(Activity activity,String question) {
        SharedPreferences prefs=activity.getSharedPreferences("home_ai",Context.MODE_PRIVATE);
        String endpoint=prefs.getString("endpoint","");
        String token=prefs.getString("token","");
        if(endpoint.isEmpty()||token.isEmpty())return false;
        new Thread(()->{
            String answer;
            int mood=0;
            try {
                URL target=new URL(endpoint);
                if(!"https".equalsIgnoreCase(target.getProtocol()))throw new Exception("HTTPS obrigatório");
                HttpURLConnection conn=(HttpURLConnection)target.openConnection();
                conn.setRequestMethod("POST");
                conn.setConnectTimeout(12000);conn.setReadTimeout(25000);
                conn.setRequestProperty("Authorization","Bearer "+token);
                conn.setRequestProperty("Content-Type","application/json; charset=utf-8");
                conn.setDoOutput(true);
                JSONObject body=new JSONObject();
                body.put("message",question.substring(0,Math.min(500,question.length())));
                body.put("mood",activity.getSharedPreferences("home",Context.MODE_PRIVATE).getInt("mood",0));
                try(OutputStream out=conn.getOutputStream()){out.write(body.toString().getBytes(StandardCharsets.UTF_8));}
                if(conn.getResponseCode()!=200)throw new Exception("HTTP "+conn.getResponseCode());
                ByteArrayOutputStream out=new ByteArrayOutputStream();
                try(InputStream in=conn.getInputStream()){
                    byte[] bytes=new byte[4096];int n;
                    while((n=in.read(bytes))!=-1){
                        if(out.size()+n>12000)throw new Exception("Resposta extensa");
                        out.write(bytes,0,n);
                    }
                }finally{conn.disconnect();}
                JSONObject result=new JSONObject(out.toString("UTF-8"));
                answer=result.optString("reply","Sem resposta.");
                mood=Math.max(0,Math.min(3,result.optInt("mood",0)));
            }catch(Exception e){answer="A IA está indisponível. "+e.getMessage();}
            final String message=answer;final int newMood=mood;
            activity.runOnUiThread(()->{
                if(activity.isFinishing())return;
                activity.getSharedPreferences("home",Context.MODE_PRIVATE).edit().putInt("mood",newMood).apply();
                try{activity.startService(new android.content.Intent(activity,OverlayService.class));}
                catch(Exception ignored){}
                HomeVoice.speak(activity,message);
                show(activity,message);
            });
        }).start();
        return true;
    }

    private static void show(Activity activity,String message){
        if(!activity.isFinishing())new AlertDialog.Builder(activity).setTitle("Home")
            .setMessage(message).setPositiveButton("Fechar",null).show();
    }
}
