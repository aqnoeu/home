package com.aqnoeu.home;

import android.content.Context;
import android.content.SharedPreferences;
import java.io.File;

/** Remove only the retired Home Alex model files; preserve all other settings. */
public final class VoiceCleanup {
    private VoiceCleanup() {}

    public static void cleanup(Context context) {
        SharedPreferences prefs = context.getSharedPreferences("home_cleanup",Context.MODE_PRIVATE);
        if (prefs.getBoolean("alex_removed_v1",false)) return;
        boolean success = true;
        success &= delete(new File(context.getFilesDir(),"kokoro-alex-pt-v1"));
        success &= delete(new File(context.getFilesDir(),"kokoro-alex-staging"));
        success &= delete(new File(context.getCacheDir(),"alex-model-download.zip"));
        // Do not touch files stored outside the app or other models.
        if(success) prefs.edit().putBoolean("alex_removed_v1",true).apply();
    }

    private static boolean delete(File file) {
        if(!file.exists()) return true;
        if(file.isDirectory()) {
            File[] children = file.listFiles();
            if(children==null) return false;
            for(File child:children) if(!delete(child)) return false;
        }
        return file.delete();
    }
}
