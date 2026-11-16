package com.aqnoeu.home;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

public final class UpdateHelper {
    private static final String API = "https://api.github.com/repos/aqnoeu/home/releases?per_page=20";
    private UpdateHelper() {}
    public static void check(Activity activity,TextView status) {
        status.setText("Consultando versões Android no GitHub...");
        new Thread(()->{
            String url = null, version = null;
            String error=null;
            try {
                HttpURLConnection conn=(HttpURLConnection)new URL(API).openConnection();
                conn.setConnectTimeout(10000); conn.setReadTimeout(10000);
                conn.setRequestProperty("Accept","application/vnd.github+json");
                conn.setRequestProperty("User-Agent","Home-Android");
                if(conn.getResponseCode()!=200)throw new Exception("HTTP "+conn.getResponseCode());
                ByteArrayOutputStream out=new ByteArrayOutputStream();
                try(InputStream stream=conn.getInputStream()){
                    byte[] buffer=new byte[4096];int n;
                    while((n=stream.read(buffer))!=-1) {
                        if(out.size()>512000)throw new Exception("Resposta excessiva");
                        out.write(buffer,0,n);
                    }
                } finally {conn.disconnect();}
                JSONArray releases=new JSONArray(out.toString(StandardCharsets.UTF_8.name()));
                for(int i=0;i<releases.length() && url==null;i++) {
                    JSONObject release=releases.getJSONObject(i);
                    if(release.optBoolean("draft")||release.optBoolean("prerelease"))continue;
                    JSONArray assets=release.optJSONArray("assets");if(assets==null)continue;
                    for(int j=0;j<assets.length();j++){
                        JSONObject asset=assets.getJSONObject(j);
                        if("Home-Android.apk".equals(asset.optString("name"))){
                            url=asset.getString("browser_download_url");
                            version=release.optString("tag_name","sem versão");
                            break;
                        }
                    }
                }
            } catch(Exception ex){error=ex.getMessage();}
            final String download=url, tag=version, issue=error;
            activity.runOnUiThread(()->{
                if(activity.isFinishing())return;
                if(issue!=null){status.setText("Falha na verificação: "+issue);return;}
                if(download==null){status.setText("Ainda não existe APK Android publicado nas Releases.");return;}
                status.setText("Versão Android disponível: "+tag+" • instalada: "+BuildConfig.VERSION_NAME);
                new AlertDialog.Builder(activity).setTitle("Home Android — "+tag)
                    .setMessage("Deseja abrir o download oficial no GitHub? O Android solicitará confirmação para instalar. Verifique se a versão é mais recente.")
                    .setPositiveButton("Abrir APK",(d,w)->activity.startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(download))))
                    .setNegativeButton("Cancelar",null).show();
            });
        }).start();
    }
}
