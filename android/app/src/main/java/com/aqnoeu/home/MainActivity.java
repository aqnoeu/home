package com.aqnoeu.home;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.*;
import android.graphics.*;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.widget.*;
import com.google.zxing.BarcodeFormat;
import com.google.zxing.MultiFormatWriter;
import com.google.zxing.common.BitMatrix;

public final class MainActivity extends Activity {
    private LinearLayout root;
    private TextView status;
    private static final String DOWNLOAD = "https://github.com/aqnoeu/home/releases";
    private final int background = Color.rgb(23,24,26);
    private final int card = Color.rgb(38,40,42);
    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private GradientDrawable shape(int color,int radius) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color); d.setCornerRadius(dp(radius)); d.setStroke(dp(1),Color.rgb(66,68,70));
        return d;
    }
    private TextView text(String value,int size) {
        TextView t = new TextView(this);
        t.setText(value); t.setTextColor(Color.rgb(235,237,240)); t.setTextSize(size);
        t.setPadding(dp(4),dp(8),dp(4),dp(8));
        return t;
    }
    private void addButton(String title, Runnable action) {
        Button b = new Button(this);
        b.setText(title); b.setTextColor(Color.WHITE); b.setAllCaps(false);
        b.setBackground(shape(card,12));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1,dp(54));
        p.bottomMargin=dp(8); root.addView(b,p);
        b.setOnClickListener(v -> action.run());
    }
    private void showStatus(String value) { status.setText(value); }
    @Override public void onCreate(Bundle bundle) {
        super.onCreate(bundle);
        getWindow().setStatusBarColor(background);
        getWindow().setNavigationBarColor(background);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true); scroll.setBackgroundColor(background);
        root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(22),dp(24),dp(22),dp(24)); scroll.addView(root);
        setContentView(scroll);
        TextView heading=text("Home",28); root.addView(heading);
        TextView sub=text("Notch animado • Android",13); sub.setTextColor(0xffa4a6aa); root.addView(sub);
        EyesView eyes = new EyesView(this);
        eyes.setMood(getPreferences(MODE_PRIVATE).getInt("mood",0));
        eyes.setBackground(shape(Color.rgb(5,7,11),20));
        root.addView(eyes,new LinearLayout.LayoutParams(-1,dp(85)));
        root.addView(text("Expressão",17));
        String[] moods = {"Normal","Amigável","Sonolento","Bravo"};
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        root.addView(row);
        for(int i=0;i<moods.length;i++) {
            final int index=i;
            Button btn=new Button(this); btn.setText(moods[i]); btn.setTextSize(10); btn.setAllCaps(false);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0,dp(50),1); lp.setMargins(dp(2),0,dp(2),0);
            row.addView(btn,lp);
            btn.setOnClickListener(v -> {
                getPreferences(MODE_PRIVATE).edit().putInt("mood",index).apply();
                getSharedPreferences("home",MODE_PRIVATE).edit().putInt("mood",index).apply();
                eyes.setMood(index);
                if(Settings.canDrawOverlays(this)) startService(new Intent(this,OverlayService.class));
            });
        }
        root.addView(text("Posição do Notch • Xiaomi 13 Pro",17));
        android.content.SharedPreferences prefs = getSharedPreferences("home",MODE_PRIVATE);
        Switch edgeSwitch = new Switch(this);
        edgeSwitch.setText("Tentar posicionar atrás da barra transparente");
        edgeSwitch.setTextColor(Color.WHITE);
        edgeSwitch.setChecked(prefs.getBoolean("edge_mode",true));
        root.addView(edgeSwitch);
        edgeSwitch.setOnCheckedChangeListener((v,checked)->{
            prefs.edit().putBoolean("edge_mode",checked).apply();
            refreshNotch();
        });
        addPositionControl("Horizontal • esquerda / direita", "offset_x", -180, 180, 100);
        addPositionControl("Vertical • subir / descer", "offset_y", -60, 120, 0);
        addPositionControl("Aba de toque • altura", "handle_y", 0, 48, 4);
        Switch touch = new Switch(this);
        touch.setText("Mostrar aba de toque abaixo da barra");
        touch.setTextColor(Color.WHITE);
        touch.setChecked(prefs.getBoolean("touch_tab",true));
        root.addView(touch);
        touch.setOnCheckedChangeListener((button,enabled) -> {
            prefs.edit().putBoolean("touch_tab",enabled).apply();
            refreshNotch();
        });
        addButton("Restaurar posição para Xiaomi 13 Pro",()->{
            prefs.edit().putInt("offset_x",100).putInt("offset_y",0)
                .putBoolean("edge_mode",true).apply();
            refreshNotch();
            new AlertDialog.Builder(this).setMessage("Posição restaurada. Reabra a tela para atualizar os controles.")
                .setPositiveButton("OK",null).show();
        });
        root.addView(text("Personalidade do Home",17));
        TextView personalityNote = text("O Home já reage a interações simples, sem usar microfone nem enviar dados. A conversa por IA dependerá de um servidor seguro.",12);
        personalityNote.setTextColor(0xffaaadb0);
        root.addView(personalityNote);
        addButton("✨ Me surpreenda", () -> localReaction("surprise"));
        addButton("♡ Como você está?", () -> localReaction("mood"));
        addButton("🎉 Comemorar!", () -> localReaction("celebrate"));
        root.addView(text("Notch",17));
        addButton("Ativar Notch",()->{
            if (!Settings.canDrawOverlays(this)) {
                startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+getPackageName())));
                showStatus("Autorize a sobreposição e depois toque em Ativar Notch.");
                return;
            }
            if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=android.content.pm.PackageManager.PERMISSION_GRANTED)
                requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},1);
            try { startForegroundService(new Intent(this,OverlayService.class)); showStatus("Notch ativado. Use a tela inicial para testar."); }
            catch(Exception e) { showStatus("Não foi possível iniciar: "+e.getMessage()); }
        });
        addButton("Desativar Notch",()->{stopService(new Intent(this,OverlayService.class));showStatus("Notch desativado.");});
        addButton("Verificar atualizações",()->UpdateHelper.check(this,status));
        addButton("Baixar / compartilhar Home (QR Code)",this::showQR);
        addButton("Abrir página de downloads",()->startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(DOWNLOAD))));
        status=text("O Notch requer autorização para aparecer sobre outros aplicativos. Sua posição pode variar conforme o Android e a câmera frontal.",12);
        status.setTextColor(0xffb8bac0); root.addView(status);
        root.addView(text("Desenvolvido com @aqnoeu • v"+BuildConfig.VERSION_NAME,12));
    }
    private void localReaction(String command) {
        String response;
        int mood;
        java.util.Random random = new java.util.Random();
        if ("celebrate".equals(command)) {
            mood=1;
            String[] messages={"Oba! Hoje estou cheio de energia! ✨", "Vitória! Piscadinha de comemoração! 🎉"};
            response=messages[random.nextInt(messages.length)];
        } else if ("mood".equals(command)) {
            int hour=java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY);
            mood=hour>=22 || hour<7 ? 2 : 0;
            response=mood==2 ? "Estou ficando sonolento... mas ainda estou aqui. 🌙" : "Estou atento e curioso! E você?";
        } else {
            mood=random.nextInt(3);
            String[] messages={"Psst... gostei de ter companhia! 👀", "Você encontrou minha expressão secreta! ✨", "Hoje eu só quero ficar olhando as estrelas. 🌟"};
            response=messages[random.nextInt(messages.length)];
        }
        getSharedPreferences("home",MODE_PRIVATE).edit().putInt("mood",mood).apply();
        refreshNotch();
        new AlertDialog.Builder(this).setTitle("Home").setMessage(response)
            .setPositiveButton("Legal!",null).show();
    }
    private void refreshNotch() {
        if (Settings.canDrawOverlays(this)) {
            try { startService(new Intent(this,OverlayService.class)); }
            catch (RuntimeException e) { showStatus("Não foi possível aplicar a posição: "+e.getMessage()); }
        }
    }
    private void addPositionControl(String title,String key,int minimum,int maximum,int defaultValue) {
        android.content.SharedPreferences prefs = getSharedPreferences("home",MODE_PRIVATE);
        TextView label = text(title+": "+prefs.getInt(key,defaultValue)+" dp",13);
        root.addView(label);
        SeekBar slider = new SeekBar(this);
        slider.setMax(maximum-minimum);
        slider.setProgress(Math.max(0,Math.min(maximum-minimum,prefs.getInt(key,defaultValue)-minimum)));
        root.addView(slider);
        slider.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar bar,int progress,boolean fromUser) {
                if(!fromUser)return;
                int value=minimum+progress;
                label.setText(title+": "+value+" dp");
                prefs.edit().putInt(key,value).apply();
                refreshNotch();
            }
            @Override public void onStartTrackingTouch(SeekBar bar) {}
            @Override public void onStopTrackingTouch(SeekBar bar) {}
        });
    }
    private void showQR() {
        try {
            BitMatrix matrix = new MultiFormatWriter().encode(DOWNLOAD,BarcodeFormat.QR_CODE,360,360);
            Bitmap bmp=Bitmap.createBitmap(360,360,Bitmap.Config.ARGB_8888);
            for(int y=0;y<360;y++)for(int x=0;x<360;x++)bmp.setPixel(x,y,matrix.get(x,y)?Color.BLACK:Color.WHITE);
            ImageView view=new ImageView(this); view.setImageBitmap(bmp);
            new android.app.AlertDialog.Builder(this).setTitle("Instale o Home no Android")
                .setMessage("Escaneie o QR Code e procure o arquivo Home-Android.apk na versão publicada.")
                .setView(view).setPositiveButton("Abrir downloads",(d,w)->startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(DOWNLOAD))))
                .setNegativeButton("Fechar",null).show();
        } catch(Exception e) { showStatus("Não foi possível gerar QR Code: "+e.getMessage()); }
    }
}
