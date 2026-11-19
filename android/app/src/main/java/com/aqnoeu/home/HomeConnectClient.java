package com.aqnoeu.home;

import android.content.Context;
import org.json.JSONObject;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URI;
import java.net.URL;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;

/** Explicit read-only HTTPS request to a user-configured API; no auto-execution by AI. */
public final class HomeConnectClient {
    private HomeConnectClient(){}
    private static boolean publicAddress(InetAddress a){
        return !(a.isAnyLocalAddress()||a.isLoopbackAddress()||a.isLinkLocalAddress()
            ||a.isSiteLocalAddress()||a.isMulticastAddress());
    }
    public static String test(Context context,String name) throws Exception {
        JSONObject entry=HomeConnectStore.privateProfile(context,name);
        if(entry==null)throw new IllegalArgumentException("Conexão não encontrada.");
        URI uri=new URI(entry.getString("url"));
        if(!"https".equalsIgnoreCase(uri.getScheme())||uri.getHost()==null
            ||uri.getPort()!=-1||uri.getUserInfo()!=null)
            throw new IllegalArgumentException("Somente HTTPS público é aceito.");
        for(InetAddress ip:InetAddress.getAllByName(uri.getHost())){
            if(!publicAddress(ip))throw new SecurityException("Endereço privado ou local bloqueado.");
        }
        HttpURLConnection conn=(HttpURLConnection)new URL(uri.toString()).openConnection();
        try{
            conn.setRequestMethod("GET");
            conn.setInstanceFollowRedirects(false);
            conn.setConnectTimeout(7000);conn.setReadTimeout(10000);
            conn.setRequestProperty("Accept","application/json, text/plain");
            String key=entry.optString("key","");
            if(!key.isEmpty())conn.setRequestProperty("Authorization","Bearer "+key);
            int code=conn.getResponseCode();
            if(code>=300&&code<400)return "HTTP "+code+" — redirecionamento bloqueado por segurança.";
            if(code==401||code==403)return "HTTP "+code+" — verifique a chave e as permissões.";
            InputStream stream=code>=400?conn.getErrorStream():conn.getInputStream();
            if(stream==null)return "HTTP "+code+" — sem corpo de resposta.";
            try(InputStream in=stream; ByteArrayOutputStream out=new ByteArrayOutputStream()){
                byte[] buf=new byte[1024];int n;
                while((n=in.read(buf))!=-1){
                    if(out.size()+n>4096)throw new IllegalStateException("Resposta maior que 4 KB; prévia cancelada.");
                    out.write(buf,0,n);
                }
                String body=new String(out.toByteArray(),StandardCharsets.UTF_8);
                return "HTTP "+code+" · "+(body.trim().isEmpty()?"Sem conteúdo":body);
            }
        }finally{conn.disconnect();}
    }
}
