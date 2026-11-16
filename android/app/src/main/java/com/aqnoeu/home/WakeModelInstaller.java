package com.aqnoeu.home;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Instala o modelo pt-BR apenas após o usuário ativar a opção Ei Home.
 * Modelo e checksum são os mesmos já usados pelo HOME Windows.
 */
public final class WakeModelInstaller {
    private static final String NAME = "vosk-model-small-pt-0.3";
    private static final String URL = "https://alphacephei.com/vosk/models/" + NAME + ".zip";
    private static final String SHA256 = "6e1ce909032e1afa7a88e68a3d628ecafff302bdf195befab308826c395e93b7";
    private static final long MAX_DOWNLOAD = 65L * 1024 * 1024;
    private static final long MAX_UNPACKED = 250L * 1024 * 1024;
    private static final AtomicBoolean busy = new AtomicBoolean(false);
    private static final Handler main = new Handler(Looper.getMainLooper());
    public interface Callback { void done(boolean ok, String message); }
    private WakeModelInstaller() {}

    public static File folder(Context context) { return new File(context.getFilesDir(), NAME); }
    public static boolean installed(Context context) {
        File f = folder(context);
        return new File(f,"final.mdl").isFile() && new File(f,"mfcc.conf").isFile()
            && new File(f,"Gr.fst").isFile() && new File(f,"HCLr.fst").isFile()
            || new File(f,"am/final.mdl").isFile() && new File(f,"conf/model.conf").isFile()
            && new File(f,"graph/Gr.fst").isFile();
    }
    public static void install(Context context, Callback callback) {
        if(installed(context)) { main.post(()->callback.done(true,"Modelo de português pronto."));return; }
        if(!busy.compareAndSet(false,true)) {
            main.post(()->callback.done(false,"O modelo de ativação já está sendo instalado."));return;
        }
        Context app=context.getApplicationContext();
        new Thread(()->{
            File staging=new File(app.getCacheDir(),"home-wake-model-staging");
            File archive=new File(app.getCacheDir(),"home-wake-model.zip");
            boolean ok=false;
            String message;
            try {
                if(app.getFilesDir().getUsableSpace()<260L*1024*1024)
                    throw new IOException("É necessário liberar espaço para instalar o reconhecimento local.");
                delete(staging);
                if(!staging.mkdirs())throw new IOException("Não foi possível preparar a pasta temporária.");
                MessageDigest digest=MessageDigest.getInstance("SHA-256");
                HttpURLConnection conn=(HttpURLConnection)new URL(URL).openConnection();
                conn.setConnectTimeout(20000);
                conn.setReadTimeout(60000);
                conn.setInstanceFollowRedirects(true);
                try {
                    if(conn.getResponseCode()!=200)throw new IOException("Download HTTP "+conn.getResponseCode());
                    long count=0;
                    try(InputStream input=conn.getInputStream(); OutputStream out=new FileOutputStream(archive)) {
                        byte[] buffer=new byte[65536];int n;
                        while((n=input.read(buffer))!=-1) {
                            count+=n;
                            if(count>MAX_DOWNLOAD)throw new IOException("Download maior que o permitido.");
                            digest.update(buffer,0,n);out.write(buffer,0,n);
                        }
                    }
                } finally {conn.disconnect();}
                StringBuilder actual=new StringBuilder();
                for(byte b:digest.digest())actual.append(String.format(java.util.Locale.ROOT,"%02x",b & 255));
                if(!SHA256.equals(actual.toString()))throw new IOException("Assinatura SHA-256 do modelo não confere.");
                long unpacked=0;
                try(ZipInputStream zip=new ZipInputStream(new FileInputStream(archive))) {
                    ZipEntry entry;byte[] buffer=new byte[65536];
                    while((entry=zip.getNextEntry())!=null) {
                        if(entry.isDirectory())continue;
                        String path=entry.getName().replace('\\','/');
                        if(!path.startsWith(NAME+"/"))continue;
                        String relative=path.substring(NAME.length()+1);
                        if(relative.isEmpty() || relative.contains("..") || relative.startsWith("/"))continue;
                        File output=new File(staging,relative).getCanonicalFile();
                        if(!output.getPath().startsWith(staging.getCanonicalPath()+File.separator))
                            throw new IOException("Entrada de ZIP inválida.");
                        File parent=output.getParentFile();
                        if(!parent.isDirectory()&&!parent.mkdirs())throw new IOException("Pasta inválida.");
                        try(OutputStream out=new FileOutputStream(output)){
                            int n;
                            while((n=zip.read(buffer))!=-1) {
                                unpacked+=n;if(unpacked>MAX_UNPACKED)throw new IOException("Modelo extraído excede o limite.");
                                out.write(buffer,0,n);
                            }
                        }
                        zip.closeEntry();
                    }
                }
                // Verificação ainda na pasta temporária antes da substituição.
                if(!(new File(staging,"final.mdl").isFile() && new File(staging,"mfcc.conf").isFile()
                    && new File(staging,"Gr.fst").isFile() && new File(staging,"HCLr.fst").isFile())
                    && !(new File(staging,"am/final.mdl").isFile() && new File(staging,"conf/model.conf").isFile()
                    && new File(staging,"graph/Gr.fst").isFile()))
                    throw new IOException("Modelo de voz extraído está incompleto.");
                File target=folder(app);
                delete(target);
                if(!staging.renameTo(target))throw new IOException("Não foi possível instalar o modelo.");
                ok=true;
                message="✓ Modelo de ativação offline instalado.";
            }catch(Exception e) {
                message="Falha ao instalar a ativação offline: "+e.getMessage();
            }finally{
                archive.delete();delete(staging);busy.set(false);
            }
            final boolean success=ok;final String result=message;
            main.post(()->callback.done(success,result));
        },"home-wake-model-install").start();
    }
    private static void delete(File file) {
        if(file.isDirectory()){
            File[] children=file.listFiles();
            if(children!=null)for(File child:children)delete(child);
        }
        if(file.exists())file.delete();
    }
}
