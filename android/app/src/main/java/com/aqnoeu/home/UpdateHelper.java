package com.aqnoeu.home;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.widget.TextView;
import androidx.core.content.FileProvider;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

/** Checks official signed Android releases; downloads and launches system installer with consent. */
public final class UpdateHelper {
    private static final String API = "https://api.github.com/repos/aqnoeu/home/releases?per_page=30";
    private static final String RELEASE_BASE = "https://github.com/aqnoeu/home/releases/download/";
    private static final long MAX_APK = 150L * 1024 * 1024;
    private UpdateHelper() {}

    public static void check(Activity activity, TextView status) {
        status.setText("Consultando atualizações oficiais do Home Android...");
        new Thread(() -> {
            try {
                JSONArray releases = new JSONArray(new String(readLimited(API, 700000), StandardCharsets.UTF_8));
                JSONObject selected = null;
                JSONObject selectedAsset = null;
                int current = versionCode(activity);
                int newest = current;
                for (int i = 0; i < releases.length(); i++) {
                    JSONObject release = releases.getJSONObject(i);
                    if (release.optBoolean("draft") || release.optBoolean("prerelease")) continue;
                    String tag = release.optString("tag_name");
                    if (!tag.matches("android-v\\d+\\.\\d+\\.\\d+")) continue;
                    int candidate = versionCodeForTag(tag);
                    if (candidate <= newest) continue;
                    JSONArray assets = release.optJSONArray("assets");
                    if (assets == null) continue;
                    for (int j = 0; j < assets.length(); j++) {
                        JSONObject item = assets.getJSONObject(j);
                        if ("Home-Android.apk".equals(item.optString("name"))) {
                            String url = item.optString("browser_download_url");
                            String sha = item.optString("digest");
                            if (!validReleaseUrl(url) || !sha.matches("sha256:[a-fA-F0-9]{64}")) continue;
                            selected = release; selectedAsset = item; newest = candidate;
                            break;
                        }
                    }
                }
                if (selectedAsset == null) {
                    ui(activity, () -> status.setText("Home Android atualizado (v" + BuildConfig.VERSION_NAME +
                        "). Se houver um APK de teste mais novo, ele ainda não é uma atualização oficial assinada."));
                    return;
                }
                final String tag = selected.optString("tag_name");
                final String url = selectedAsset.getString("browser_download_url");
                final String digest = selectedAsset.getString("digest").substring(7).toLowerCase(Locale.ROOT);
                final long size = selectedAsset.optLong("size", 0);
                if (size <= 0 || size > MAX_APK) throw new IOException("APK fora do limite de segurança");
                ui(activity, () -> {
                    status.setText("Atualização disponível: " + tag + " (instalada: " + BuildConfig.VERSION_NAME + ")");
                    new AlertDialog.Builder(activity).setTitle("Atualização do Home — " + tag)
                        .setMessage("Baixar a versão Android assinada e abrir o instalador do sistema? As configurações serão preservadas se a assinatura for compatível.")
                        .setPositiveButton("Baixar e instalar", (dialog, which) -> download(activity, status, url, digest, size))
                        .setNegativeButton("Agora não", null).show();
                });
            } catch (Exception e) {
                ui(activity, () -> status.setText("Não foi possível verificar atualizações: " + e.getMessage()));
            }
        }).start();
    }

    private static void download(Activity activity, TextView status, String url, String digest, long size) {
        status.setText("Baixando atualização do Home...");
        new Thread(() -> {
            File output = new File(activity.getCacheDir(), "home_update.apk");
            try {
                if (!validReleaseUrl(url)) throw new IOException("Endereço de download inesperado");
                HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
                c.setConnectTimeout(15000); c.setReadTimeout(45000);
                c.setRequestProperty("User-Agent", "Home-Android-Updater");
                try {
                    c.connect();
                    String host = c.getURL().getHost();
                    if (!(host.equals("github.com") || host.equals("release-assets.githubusercontent.com")
                        || host.equals("objects.githubusercontent.com"))) throw new IOException("Servidor inesperado");
                    if (c.getResponseCode() != 200) throw new IOException("Download HTTP " + c.getResponseCode());
                    MessageDigest md = MessageDigest.getInstance("SHA-256");
                    long total = 0;
                    try (InputStream stream = c.getInputStream(); FileOutputStream out = new FileOutputStream(output)) {
                        byte[] buffer = new byte[65536];
                        int n;
                        while ((n = stream.read(buffer)) >= 0) {
                            if (n == 0) continue;
                            total += n;
                            if (total > MAX_APK || total > size) throw new IOException("APK excedeu o tamanho anunciado");
                            out.write(buffer, 0, n); md.update(buffer, 0, n);
                        }
                    }
                    if (total != size) throw new IOException("Download incompleto");
                    StringBuilder actual = new StringBuilder();
                    for (byte b : md.digest()) actual.append(String.format(Locale.ROOT, "%02x", b & 0xff));
                    if (!actual.toString().equals(digest)) throw new IOException("Falha na integridade SHA-256");
                } finally { c.disconnect(); }
                ui(activity, () -> {
                    status.setText("Download verificado. Confirme a instalação no Android.");
                    Uri apk = FileProvider.getUriForFile(activity,
                        activity.getPackageName() + ".fileprovider", output);
                    Intent install = new Intent(Intent.ACTION_VIEW);
                    install.setDataAndType(apk, "application/vnd.android.package-archive");
                    install.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    try {
                        if (Build.VERSION.SDK_INT >= 26 && !activity.getPackageManager().canRequestPackageInstalls()) {
                            status.setText("Autorize a instalação de apps pelo Home nas configurações e tente novamente.");
                            activity.startActivity(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                                Uri.parse("package:" + activity.getPackageName())));
                        } else activity.startActivity(install);
                    } catch (Exception e) { status.setText("Não foi possível abrir o instalador: " + e.getMessage()); }
                });
            } catch (Exception e) {
                output.delete();
                ui(activity, () -> status.setText("Download cancelado: " + e.getMessage()));
            }
        }).start();
    }

    private static int versionCode(Activity activity) {
        if (Build.VERSION.SDK_INT >= 28) {
            try { return (int)activity.getPackageManager().getPackageInfo(activity.getPackageName(), 0).getLongVersionCode(); }
            catch (Exception ignored) {}
        }
        return BuildConfig.VERSION_CODE;
    }
    private static int versionCodeForTag(String tag) {
        try {
            String[] v = tag.substring("android-v".length()).split("\\.");
            return Integer.parseInt(v[0]) * 10000 + Integer.parseInt(v[1]) * 100 + Integer.parseInt(v[2]);
        } catch (Exception e) { return -1; }
    }
    private static boolean validReleaseUrl(String url) {
        return url.startsWith(RELEASE_BASE) && url.endsWith("/Home-Android.apk");
    }
    private static byte[] readLimited(String url, int limit) throws IOException {
        HttpURLConnection conn = (HttpURLConnection)new URL(url).openConnection();
        conn.setConnectTimeout(12000); conn.setReadTimeout(12000);
        conn.setRequestProperty("Accept", "application/vnd.github+json");
        conn.setRequestProperty("User-Agent", "Home-Android-Updater");
        try {
            if (conn.getResponseCode() != 200) throw new IOException("GitHub HTTP " + conn.getResponseCode());
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            try (InputStream in = conn.getInputStream()) {
                byte[] bytes = new byte[8192]; int n;
                while ((n = in.read(bytes)) != -1) {
                    if (buffer.size() + n > limit) throw new IOException("Resposta muito grande");
                    buffer.write(bytes, 0, n);
                }
            }
            return buffer.toByteArray();
        } finally { conn.disconnect(); }
    }
    private static void ui(Activity activity, Runnable action) {
        activity.runOnUiThread(() -> { if (!activity.isFinishing() && !activity.isDestroyed()) action.run(); });
    }
}
