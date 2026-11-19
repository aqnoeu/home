package com.aqnoeu.home;

import android.Manifest;
import android.app.Activity;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.*;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.text.InputType;
import android.text.SpannableString;
import android.text.style.ForegroundColorSpan;
import android.view.*;
import android.view.inputmethod.InputMethodManager;
import android.widget.*;
import com.google.zxing.BarcodeFormat;
import com.google.zxing.MultiFormatWriter;
import com.google.zxing.common.BitMatrix;
import org.json.JSONArray;
import org.json.JSONObject;
import java.text.DateFormat;
import java.util.Date;

/**
 * HOME mobile, Brand Guidelines 1.2.
 * No Home-generated modal dialogs: decisions, diagnostics, forms, QR and states
 * are displayed within the current page. Android system permission/installer UI
 * and the device's speech recognition UI are controlled by Android itself.
 */
public final class MainActivity extends Activity {
    private static final String DOWNLOAD = "https://github.com/aqnoeu/home/releases";
    private static volatile boolean inForeground=false;
    public static boolean isInForeground(){return inForeground;}
    @Override protected void onResume(){
        super.onResume();
        inForeground=true;
        // Background speech is persisted by the service; reread it when opening the app.
        if("assistant".equals(currentPage))refreshChat();
    }
    @Override protected void onPause(){inForeground=false;super.onPause();}
    private static final int BG = Color.rgb(11,17,26);           // #0B111A
    private static final int SURFACE = Color.rgb(20,29,42);
    private static final int RAISED = Color.rgb(29,40,56);
    private static final int LINE = Color.rgb(49,62,80);
    private static final int WHITE = Color.WHITE;
    private static final int MUTED = Color.rgb(176,188,204);
    private static final int BLUE = Color.rgb(47,107,255);       // #2F6BFF actions
    private static final int ORANGE = Color.rgb(255,106,0);      // #FF6A00 editorial
    private static final int GREEN = Color.rgb(0,196,106);      // #00C46A success
    private LinearLayout root, inlineHost;
    private ScrollView scroll;
    private TextView status;
    private LinearLayout chatMessages, chatPicker;
    private ScrollView chatScroll;
    private android.widget.EditText chatInput;
    private final Handler wakeHandler=new Handler(Looper.getMainLooper());
    private TextView chatTitle;
    private String currentPage = "assistant";
    private String settingsTab = "Geral";
    private HomeHubAccount unifiedAccount;
    private static final int WAKE_PERMISSION_REQUEST = 721;
    private static final int WAKE_NOTIFICATION_PERMISSION_REQUEST = 722;
    private boolean wakeBusy = false;
    private static final int VOICE_ENROLL_REQUEST = 815;

    private final HomeUiKit ui=new HomeUiKit(this);
    private int dp(float n){return ui.dp(n);}
    private boolean narrow(){return ui.narrow();}
    private GradientDrawable bg(int color,int radius){return ui.bg(color,radius);}
    private TextView text(String value,int sp,int color,boolean heavy){return ui.text(value,sp,color,heavy);}
    private TextView text(String value,int sp){return ui.text(value,sp);}
    private TextView heading(String value,int sp){return ui.heading(value,sp);}
    private TextView note(String value){return ui.note(value);}
    private LinearLayout.LayoutParams space(int top,int bottom){return ui.space(top,bottom);}
    private void add(LinearLayout host,View view,int top,int bottom){ui.add(host,view,top,bottom);}
    private LinearLayout column(){return ui.column();}
    private LinearLayout card(String title,String description){return ui.card(title,description);}
    private Button button(String value,boolean primary,Runnable click){return ui.button(value,primary,click);}
    private void action(LinearLayout target,String label,boolean primary,Runnable run){ui.action(target,label,primary,run);}
    private void actions(LinearLayout target,String left,Runnable a,String right,Runnable b){ui.actions(target,left,a,right,b);}
    private EditText edit(String hint,boolean secret){return ui.edit(hint,secret);}

    private void showStatus(String value){if(status!=null)status.setText(value);}
    public void reportVoiceStatus(String message){statusMessage(message);}
    private void success(TextView view,String message){view.setText("✓ "+message);view.setTextColor(GREEN);}
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);
        VoiceCleanup.cleanup(this);
        showPage("assistant");
        restoreGroqFromAccount();
        handleWakeIntent(getIntent());
    }
    @Override protected void onNewIntent(Intent intent){
        super.onNewIntent(intent);setIntent(intent);handleWakeIntent(intent);
    }
    private void handleWakeIntent(Intent intent){
        if(intent==null || !intent.hasExtra(WakeWordService.EXTRA_QUERY))return;
        String query=intent.getStringExtra(WakeWordService.EXTRA_QUERY);
        intent.removeExtra(WakeWordService.EXTRA_QUERY);
        if(query==null)return;
        try{getSystemService(android.app.NotificationManager.class).cancel(73);}catch(Exception ignored){}
        wakeBusy=true;
        pauseWake();
        showPage("assistant");
        if(query.trim().isEmpty()){
            statusMessage("Estou ouvindo. Pode falar.");
            pauseWake(true);
            if(!HomeVoice.listen(this))resumeWake();
        }else{
            // Wake-word commands use the same offline command catalog as typed chat.
            if(handleLocalCommand(query,true))return;
            statusMessage("Você: "+query+" · HOME está pensando…");
            askHome(query,null);
        }
    }
    private void startWake(){
        if(!WakeWordService.enabled(this))return;
        if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},WAKE_PERMISSION_REQUEST);
            return;
        }
        if(!getSharedPreferences("home",MODE_PRIVATE).getBoolean("notch_active",false)){
            statusMessage("Ative o Notch para iniciar a escuta.");return;
        }
        if(Build.VERSION.SDK_INT>=33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED &&
            !getSharedPreferences("home",MODE_PRIVATE).getBoolean("wake_notification_asked",false)){
            getSharedPreferences("home",MODE_PRIVATE).edit().putBoolean("wake_notification_asked",true).apply();
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},WAKE_NOTIFICATION_PERMISSION_REQUEST);
            return;
        }
        if(!WakeModelInstaller.installed(this)){
            statusMessage("Instalando reconhecimento local pt-BR (~31 MB). O áudio permanecerá no aparelho.");
            WakeModelInstaller.install(this,(ok,message)->{
                if(status!=null)statusMessage(message);
                if(ok && WakeWordService.enabled(this))startWake();
                else if(!ok && !message.contains("já está sendo instalado")){
                    getSharedPreferences("home",MODE_PRIVATE).edit().putBoolean("wake_enabled",false).apply();
                }
            });
            return;
        }
        try{
            startForegroundService(new Intent(this,WakeWordService.class));
            statusMessage("Ei Home / Ok Home: detector offline ativo.");
        }catch(Exception e){statusMessage("Falha ao iniciar escuta: "+e.getMessage());}
    }
    private void openVoiceListening(){
        pauseWake();
        if(!HomeVoice.listen(this))resumeWake();
    }
    private void pauseWake(){pauseWake(false);}
    private void pauseWake(boolean listeningForCommand){
        if(WakeWordService.enabled(this)){
            wakeBusy=true;
            wakeHandler.removeCallbacksAndMessages(null);
            try{
                startService(new Intent(this,WakeWordService.class)
                    .setAction(WakeWordService.PAUSE)
                    .putExtra("command_listening",listeningForCommand));
            }catch(Exception ignored){}
        }
    }
    private void reportVoiceFailure(String question,String explanation){
        try{
            HomeChatStore store=HomeChatStore.get(this);
            String session=store.ensureActive();
            store.addTo(session,"user",question);
            store.addTo(session,"assistant",explanation);
            refreshChat();
        }catch(Exception ignored){}
        statusMessage(explanation);
        if(FaberOffline.isInstalled(this))speakAnswer(explanation);
        else resumeWake();
    }
    private void speakAnswer(String answer){
        if(!getSharedPreferences("home",MODE_PRIVATE).getBoolean("voice_replies",true)){
            resumeWake();return;
        }
        if(FaberOffline.isInstalled(this)){
            getSharedPreferences("home",MODE_PRIVATE).edit()
                .putString("wake_visual_state","falando")
                .putLong("wake_visual_at",System.currentTimeMillis()).apply();
            FaberOffline.speak(this,answer,message->{
                if(message.startsWith("✓ Faber reproduzida") || message.startsWith("Falha")
                    || message.startsWith("Instale") || message.startsWith("O Home já está falando")){
                    resumeWake();
                }
            });
        }else{resumeWake();}
    }
    private void resumeWake(){
        if(!wakeBusy)return;
        wakeBusy=false;
        // Delay avoids recognition of the voice output (Faber).
        wakeHandler.removeCallbacksAndMessages(null);
        wakeHandler.postDelayed(()->{
            if(WakeWordService.enabled(this))
                try{startService(new Intent(this,WakeWordService.class).setAction(WakeWordService.RESUME));}
                catch(Exception ignored){}
        },1000);
    }
    @Override public void onRequestPermissionsResult(int request,String[] perms,int[] results){
        super.onRequestPermissionsResult(request,perms,results);
        if(request==WAKE_PERMISSION_REQUEST){
            if(results.length>0 && results[0]==PackageManager.PERMISSION_GRANTED)startWake();
            else statusMessage("Permissão de microfone negada. Ei, Home não está ouvindo.");
        }
        if(request==WAKE_NOTIFICATION_PERMISSION_REQUEST){
            startWake();
            if(results.length==0 || results[0]!=PackageManager.PERMISSION_GRANTED)
                statusMessage("Notificações bloqueadas: para conversar em segundo plano, talvez seja necessário abrir o HOME manualmente.");
        }
    }
    private void initScreen(String page,String subtitle){
        currentPage=page;
        HomeEmotion.pageChanged(page);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        getWindow().getDecorView().setSystemUiVisibility(0);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        if(Build.VERSION.SDK_INT>=29)getWindow().setNavigationBarContrastEnforced(false);
        scroll=new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BG);
        scroll.setVerticalScrollBarEnabled(false);
        root=column();
        ui.setRoot(root);
        // Android 15 edge-to-edge: use the measured system/cutout bars + breathing room.
        final int h=dp(18);
        root.setPadding(h,dp(28),h,dp(24));
        root.setOnApplyWindowInsetsListener((view,insets)->{
            if(Build.VERSION.SDK_INT>=30){
                android.graphics.Insets bars=insets.getInsets(
                    WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());
                root.setPadding(h,bars.top+dp(18),h,
                    bars.bottom+dp(18));
            }
            return insets;
        });
        scroll.addView(root,new ScrollView.LayoutParams(-1,-2));
        setContentView(scroll);
        root.requestApplyInsets();

        LinearLayout brand=new LinearLayout(this);
        brand.setOrientation(LinearLayout.HORIZONTAL);
        brand.setGravity(Gravity.CENTER_VERTICAL);
        // Static official app icon; animated eyes belong only to the notch and expression card.
        ImageView brandIcon=new ImageView(this);
        brandIcon.setImageResource(R.drawable.home_header_eyes);
        brandIcon.setScaleType(ImageView.ScaleType.FIT_CENTER);
        brandIcon.setBackground(null);
        brandIcon.setAdjustViewBounds(true);
        brandIcon.setContentDescription("Logomarca oficial HOME");
        LinearLayout.LayoutParams iconSize=new LinearLayout.LayoutParams(dp(58),dp(48));
        iconSize.rightMargin=dp(10);
        brand.addView(brandIcon,iconSize);
        LinearLayout brandCopy=column();
        add(brandCopy,heading("HOME",21),0,4);
        add(brandCopy,note("Um assistente para você."),0,0);
        brand.addView(brandCopy,new LinearLayout.LayoutParams(0,-2,1));
        add(root,brand,0,16);
        View line=new View(this);line.setBackgroundColor(LINE);
        root.addView(line,new LinearLayout.LayoutParams(-1,dp(1)));
        if(!"hub".equals(page) && !"history".equals(page) && !"settings".equals(page)){
            Button back=button("‹  Voltar",false,()->{
                if("editor".equals(currentPage))showSettings("Aparência");
                else showPage("assistant");
            });
            LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(dp(125),dp(44));
            p.topMargin=dp(12);p.bottomMargin=dp(14);
            root.addView(back,p);
        }else add(root,note("ASSISTENTE PESSOAL"),12,7);
        if(subtitle!=null&&!subtitle.isEmpty())add(root,note(subtitle),0,18);
        status=note("");status.setVisibility(View.GONE);
        status.setBackground(bg(RAISED,12));
        status.setPadding(dp(12),dp(10),dp(12),dp(10));
        add(root,status,8,10);
        inlineHost=column();root.addView(inlineHost,new LinearLayout.LayoutParams(-1,-2));
    }
    private void statusMessage(String message){
        status.setVisibility(View.VISIBLE);showStatus(message);
    }
    private void clearInline(){inlineHost.removeAllViews();}
    /** Visible, in-page confirmation shared by updater, model install, reset and delete. */
    public void requestInlineConfirm(String title,String message,Runnable accept){
        clearInline();
        LinearLayout panel=column();
        panel.setPadding(dp(16),dp(16),dp(16),dp(16));
        panel.setBackground(bg(RAISED,16));
        add(panel,heading(title,16),0,7);
        add(panel,note(message),0,14);
        actions(panel,"Confirmar",()->{
            clearInline();accept.run();
        },"Cancelar",this::clearInline);
        add(inlineHost,panel,0,17);
        if(scroll!=null && scroll.getParent()!=null)scroll.smoothScrollTo(0,0);
    }
    private void showHub(){
        initScreen("hub",null);
        TextView hello=heading("Olá, como posso ajudar?",narrow()?22:25);
        SpannableString span=new SpannableString(hello.getText());
        span.setSpan(new ForegroundColorSpan(ORANGE),0,4,0);
        hello.setText(span);
        add(root,hello,0,6);
        add(root,note("Seu assistente, no seu ritmo."),0,16);

        LinearLayout face=card(null,null);
        EyesView eyes=new EyesView(this);
        android.content.SharedPreferences prefs=getSharedPreferences("home",MODE_PRIVATE);
        eyes.setExpressionPreview(true);eyes.setMood(prefs.getInt("mood",0));eyes.setEyeGap(prefs.getInt("eye_gap",9));
        eyes.setBackground(bg(BG,18));
        LinearLayout.LayoutParams eyesSize=new LinearLayout.LayoutParams(-1,dp(86));
        eyesSize.bottomMargin=dp(8);
        face.addView(eyes,eyesSize);
        add(face,note("Expressão — escolha uma opção para visualizar e aplicar ao notch."),0,9);
        addExpressionPicker(face,eyes,prefs);

        add(root,heading("Acesso rápido",18),9,12);
        LinearLayout quick=column();
        actions(quick,"Conversar",()->showPage("assistant"),
            "Microfone",()->showPage("voice"));
        actions(quick,"Notch e Ei, Home",()->showPage("interactions"),"Ajustar aparência",this::showEditor);
        actions(quick,"Atualizações",()->showPage("updates"),"Sair",()->showPage("exit"));
        add(root,quick,0,8);

        add(root,note("HOME · v"+BuildConfig.VERSION_NAME+" · @aqnoeu"),17,0);
    }
    /** Three primary destinations: conversation, history and settings. */
    private void showPage(String page){
        if("assistant".equals(page)){
            initScreen("assistant",null);
            assistantPage();
        } else if("history".equals(page)){
            showHistory();
        } else if("settings".equals(page)){
            showSettings(settingsTab);
        } else if("editor".equals(page)){
            showEditor();
        } else {
            showSettings("Geral");
        }
    }

    private LinearLayout bottomNavigation(String active){
        LinearLayout tabs=new LinearLayout(this);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        tabs.setGravity(Gravity.CENTER_VERTICAL);
        tabs.setBackground(bg(SURFACE,16));
        tabs.setPadding(dp(3),dp(2),dp(3),dp(2));
        String[] names={"Conversar","Histórico","Ajustes"};
        String[] routes={"assistant","history","settings"};
        for(int i=0;i<names.length;i++){
            final String route=routes[i];
            Button b=button(names[i],active.equals(route),()->showPage(route));
            b.setTextSize(12);
            b.setSingleLine(true);
            b.setPadding(dp(2),0,dp(2),0);
            b.setBackground(bg(active.equals(route)?BLUE:SURFACE,12));
            LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(44),1);
            p.leftMargin=dp(2);p.rightMargin=dp(2);
            tabs.addView(b,p);
        }
        return tabs;
    }

    private void showHistory(){
        initScreen("history",null);
        add(root,heading("Histórico",24),18,6);
        add(root,note("Suas conversas ficam salvas neste aparelho."),0,16);
        action(root,"+ Nova conversa",true,()->{
            HomeChatStore.get(this).newChat();
            showPage("assistant");
        });
        chatPicker=column();
        add(root,chatPicker,5,16);
        renderChatList();
        add(root,bottomNavigation("history"),8,12);
    }

    private Switch settingSwitch(LinearLayout host,String name,String description,
                                 boolean enabled,android.widget.CompoundButton.OnCheckedChangeListener change){
        LinearLayout item=new LinearLayout(this);
        item.setOrientation(LinearLayout.HORIZONTAL);
        item.setGravity(Gravity.CENTER_VERTICAL);
        item.setPadding(dp(14),dp(11),dp(10),dp(11));
        item.setBackground(bg(RAISED,14));
        LinearLayout copy=column();
        add(copy,text(name,14,WHITE,true),0,5);
        add(copy,note(description),0,0);
        item.addView(copy,new LinearLayout.LayoutParams(0,-2,1));
        Switch control=new Switch(this);
        control.setChecked(enabled);
        control.setThumbTintList(android.content.res.ColorStateList.valueOf(WHITE));
        control.setTrackTintList(android.content.res.ColorStateList.valueOf(enabled?BLUE:LINE));
        control.setContentDescription(name);
        item.addView(control,new LinearLayout.LayoutParams(dp(64),dp(48)));
        control.setOnCheckedChangeListener((button,on)->{
            control.setTrackTintList(android.content.res.ColorStateList.valueOf(on?BLUE:LINE));
            change.onCheckedChanged(button,on);
        });
        add(host,item,4,8);
        return control;
    }

    /** Tabs change the content of the same settings page; they are not new destinations. */
    private void showSettings(String tab){
        settingsTab=tab;
        initScreen("settings",null);
        add(root,heading("Configurações",24),16,5);
        add(root,note("Ajuste o HOME sem percorrer várias telas."),0,13);
        LinearLayout tabs=new LinearLayout(this);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        String[] names={"Geral","Voz / IA","Aparência","Conta HOME"};
        for(String name:names){
            Button b=button(name,name.equals(tab),()->showSettings(name));
            b.setSingleLine(true);
            b.setTextSize(12);
            b.setBackground(bg(name.equals(tab)?BLUE:RAISED,12));
            LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(48),1);
            p.leftMargin=dp(3);p.rightMargin=dp(3);
            tabs.addView(b,p);
        }
        add(root,tabs,0,14);
        switch(tab){
            case "Voz / IA": settingsVoice();break;
            case "Aparência": settingsAppearance();break;
            case "Conta HOME": settingsAccount();break;
            default: settingsGeneral();break;
        }
        add(root,bottomNavigation("settings"),10,10);
    }


    /** Conta unificada com HOME HUB. Rede e autenticação nunca bloqueiam a interface. */
    /** On launch, restore the account session and the Groq credential after reinstall. */
    private void restoreGroqFromAccount(){
        if(unifiedAccount==null)unifiedAccount=new HomeHubAccount(this);
        final HomeHubAccount account=unifiedAccount;
        new Thread(()->{
            try{
                if(!account.connected()&&!account.resume())return;
                String key=account.restoreGroqKey();
                if(key!=null&&!key.isEmpty()){
                    HomeGroq.connect(this,key);
                    runOnUiThread(()->{
                        if("assistant".equals(currentPage))refreshChat();
                        statusMessage("Groq restaurada pela Conta HOME.");
                    });
                }else if(HomeGroq.connected(this)){
                    String local=HomeGroq.exportForAccountSync(this);
                    if(local!=null)account.backupGroqKey(local);
                }
            }catch(Exception ignored){ /* Offline remains usable; login can restore again. */ }
        },"home-groq-restore").start();
    }
    private void backupGroqToAccount(String key,TextView state){
        if(unifiedAccount==null)unifiedAccount=new HomeHubAccount(this);
        final HomeHubAccount account=unifiedAccount;
        new Thread(()->{
            try{
                if(!account.connected()&&!account.resume()){
                    runOnUiThread(()->statusMessage("Groq salva no celular. Entre na Conta HOME para sincronizar."));
                    return;
                }
                account.backupGroqKey(key);
                runOnUiThread(()->state.setText("● Groq conectada · salva na Conta HOME"));
            }catch(Exception e){
                runOnUiThread(()->statusMessage("Groq funciona neste aparelho. Backup da conta falhou: "+e.getMessage()));
            }
        },"home-groq-backup").start();
    }
    private void restoreGroqOnLogin(HomeHubAccount account){
        new Thread(()->{
            try{
                String key=account.restoreGroqKey();
                if(key!=null&&!key.isEmpty()){
                    HomeGroq.connect(this,key);
                    runOnUiThread(()->statusMessage("Groq restaurada da Conta HOME."));
                }else if(HomeGroq.connected(this)){
                    // First registration: move the existing local key into the account vault.
                    String local=HomeGroq.exportForAccountSync(this);
                    if(local!=null)account.backupGroqKey(local);
                    runOnUiThread(()->statusMessage("Groq vinculada à Conta HOME."));
                }else{
                    runOnUiThread(()->statusMessage("Conta conectada. Cadastre sua chave Groq uma vez em Voz / IA."));
                }
            }catch(Exception e){runOnUiThread(()->statusMessage("Conta conectada; sincronização Groq indisponível."));}
        },"home-groq-on-login").start();
    }

    private void settingsAccount(){
        if(unifiedAccount==null)unifiedAccount=new HomeHubAccount(this);
        final HomeHubAccount account=unifiedAccount;
        LinearLayout section=card("Conta HOME","Use o mesmo e-mail e senha do Home Hub, no navegador e no Windows.");
        final TextView state=note(account.connected()?"Conectado: "+account.email():"Nenhuma conta vinculada neste aparelho.");
        add(section,state,0,10);
        final EditText email=edit("E-mail do Home Hub",false);
        email.setSingleLine(true);email.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        final EditText password=edit("Senha da conta HOME",true);
        add(section,email,0,6);add(section,password,0,9);
        action(section,"Entrar com conta HOME",true,()->{
            String login=email.getText().toString().trim(),pass=password.getText().toString();
            if(login.isEmpty()||pass.isEmpty()){state.setText("Digite seu e-mail e senha.");return;}
            state.setText("Autenticando com segurança...");
            new Thread(()->{
                try{account.signIn(login,pass);restoreGroqOnLogin(account);runOnUiThread(()->{password.setText("");showSettings("Conta HOME");});}
                catch(Exception e){runOnUiThread(()->state.setText("Não foi possível entrar: "+e.getMessage()));}
            },"home-account-login").start();
        });
        action(section,"Sair da conta neste celular",false,()->{
            new Thread(()->{account.signOut();runOnUiThread(()->showSettings("Conta HOME"));},"home-account-logout").start();
        });

        LinearLayout prefs=card("Sincronização autorizada","O HOME continua funcionando offline. Nenhum áudio, arquivo ou comando remoto é enviado.");
        final String[] models={"auto","qwen","glm","nemotron","gemma","llama","granite"};
        final String[] modelLabels={"Automático","Qwen 3","GLM 4.7","Nemotron 3","Gemma 4","Llama 3.3","Granite"};
        final Spinner model=new Spinner(this);
        model.setAdapter(new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,modelLabels));
        add(prefs,note("Modelo compartilhado"),0,4);add(prefs,model,0,9);
        final String[] styles={"equilibrado","objetivo","detalhado"};
        final Spinner style=new Spinner(this);
        style.setAdapter(new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,styles));
        add(prefs,note("Estilo de resposta"),0,4);add(prefs,style,0,9);
        final Switch syncChats=new Switch(this);syncChats.setText("Sincronizar conversas");syncChats.setTextColor(WHITE);
        final Switch syncEmotions=new Switch(this);syncEmotions.setText("Sincronizar preferências de emoção");syncEmotions.setTextColor(WHITE);
        add(prefs,syncChats,5,8);add(prefs,syncEmotions,0,10);
        action(prefs,"Salvar preferências no Home Hub",true,()->{
            if(!account.connected()){state.setText("Entre na sua conta antes de sincronizar.");return;}
            final String selected=models[model.getSelectedItemPosition()],tone=styles[style.getSelectedItemPosition()];
            new Thread(()->{
                try{account.savePreferences(selected,tone,syncChats.isChecked(),syncEmotions.isChecked());
                    runOnUiThread(()->state.setText("Preferências da conta HOME salvas."));}
                catch(Exception e){runOnUiThread(()->state.setText("Falha ao salvar: "+e.getMessage()));}
            },"home-account-save").start();
        });
        action(prefs,"Enviar histórico local para a conta HOME",false,()->{
            if(!account.connected()){state.setText("Entre na conta HOME.");return;}
            state.setText("Sincronizando conversas autorizadas...");
            new Thread(()->{
                try{int n=account.uploadLocalChats(HomeChatStore.get(this));
                    runOnUiThread(()->state.setText("Histórico enviado com sucesso: "+n+" mensagens."));}
                catch(Exception e){runOnUiThread(()->state.setText("Sincronização interrompida: "+e.getMessage()));}
            },"home-account-upload").start();
        });
        LinearLayout voiceCloud=card("Perfil de ativação na Conta HOME",
            "Sincronize apenas frases e correções de texto. Áudio e identificação biométrica permanecem locais.");
        action(voiceCloud,"Autorizar sincronização do perfil de voz",false,()->{
            if(!account.connected()){state.setText("Entre na Conta HOME.");return;}
            requestInlineConfirm("Sincronizar cadastro de voz",
                "Autorizar backup das frases e variantes corrigidas na Conta HOME? Nenhum áudio será enviado.",()->{
                    new Thread(()->{
                        try{account.authorizeVoiceSync();runOnUiThread(()->state.setText("✓ Sincronização do perfil de voz autorizada."));}
                        catch(Exception ex){runOnUiThread(()->state.setText("Falha: "+ex.getMessage()));}
                    },"home-voice-sync-optin").start();
                });
        });
        action(voiceCloud,"Salvar perfil Android na Conta HOME",true,()->{
            if(!account.connected()){state.setText("Entre na Conta HOME.");return;}
            new Thread(()->{
                try{account.uploadVoiceProfile(VoiceEnrollment.cloudPayload(this));
                    runOnUiThread(()->state.setText("✓ Perfil Android salvo na Conta HOME."));}
                catch(Exception ex){runOnUiThread(()->state.setText("Falha: "+ex.getMessage()));}
            },"home-voice-sync-upload").start();
        });
        action(voiceCloud,"Restaurar perfil Android desta conta",false,()->{
            if(!account.connected()){state.setText("Entre na Conta HOME.");return;}
            requestInlineConfirm("Restaurar perfil de voz",
                "Substituir as frases e correções deste Android pelo backup da Conta HOME?",()->{
                    new Thread(()->{
                        try{
                            org.json.JSONObject saved=account.downloadVoiceProfile();
                            if(saved.length()==0)throw new IllegalStateException("Nenhum perfil Android salvo na conta.");
                            VoiceEnrollment.importCloud(this,saved);
                            runOnUiThread(()->state.setText("✓ Perfil Android restaurado."));
                        }catch(Exception ex){runOnUiThread(()->state.setText("Falha: "+ex.getMessage()));}
                    },"home-voice-sync-download").start();
                });
        });
        LinearLayout history=card("Conversas no Home Hub","Leia o histórico compartilhado. Conversas locais permanecem salvas somente no celular.");
        final LinearLayout list=column();add(history,list,0,8);
        action(history,"Consultar conversas do Hub",false,()->{
            if(!account.connected()){state.setText("Entre na sua conta HOME.");return;}
            new Thread(()->{
                try{
                    org.json.JSONArray found=account.cloudChats();
                    runOnUiThread(()->{
                        list.removeAllViews();
                        if(found==null||found.length()==0){add(list,note("Nenhuma conversa na nuvem."),0,8);return;}
                        for(int i=0;i<Math.min(found.length(),30);i++){
                            final org.json.JSONObject chat=found.optJSONObject(i);
                            if(chat==null)continue;
                            final String id=chat.optString("id");
                            action(list,chat.optString("title","Conversa"),false,()->new Thread(()->{
                                try{org.json.JSONArray entries=account.cloudMessages(id);
                                    StringBuilder out=new StringBuilder();
                                    if(entries!=null)for(int j=0;j<entries.length();j++){
                                        org.json.JSONObject msg=entries.optJSONObject(j);
                                        if(msg!=null)out.append("user".equals(msg.optString("role"))?"Você: ":"HOME: ")
                                            .append(msg.optString("content")).append("\n\n");
                                    }
                                    runOnUiThread(()->{
                                        list.removeAllViews();
                                        TextView detail=note(out.toString());add(list,detail,0,8);
                                        action(list,"Voltar às conversas",false,()->showSettings("Conta HOME"));
                                    });
                                }catch(Exception e){runOnUiThread(()->state.setText(e.getMessage()));}
                            },"home-account-messages").start());
                        }
                    });
                }catch(Exception e){runOnUiThread(()->state.setText("Falha ao consultar: "+e.getMessage()));}
            },"home-account-history").start();
        });
        if(account.connected()){
            new Thread(()->{
                try{org.json.JSONObject p=account.preferences();runOnUiThread(()->{
                    if(!"settings".equals(currentPage)||!"Conta HOME".equals(settingsTab))return;
                    for(int i=0;i<models.length;i++)if(models[i].equals(p.optString("preferred_model","auto")))model.setSelection(i);
                    for(int i=0;i<styles.length;i++)if(styles[i].equals(p.optString("response_style","equilibrado")))style.setSelection(i);
                    syncChats.setChecked(p.optBoolean("sync_chats",false));
                    syncEmotions.setChecked(p.optBoolean("sync_emotions",false));
                });}catch(Exception e){runOnUiThread(()->state.setText("Preferências: "+e.getMessage()));}
            },"home-account-pref").start();
        }else{
            new Thread(()->{
                try{if(account.resume())runOnUiThread(()->showSettings("Conta HOME"));}
                catch(Exception e){runOnUiThread(()->state.setText("Sessão anterior expirada. Entre novamente."));}
            },"home-account-resume").start();
        }
    }

    private void settingsGeneral(){
        android.content.SharedPreferences prefs=getSharedPreferences("home",MODE_PRIVATE);
        LinearLayout controls=card("Notch e ativação",null);
        settingSwitch(controls,"Mostrar notch","Olhos na borda superior do celular.",
            prefs.getBoolean("notch_active",false),(view,on)->{
                if(on){
                    if(!Settings.canDrawOverlays(this)){
                        view.setChecked(false);
                        statusMessage("Autorize a sobreposição nas configurações do Android.");
                        startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                            Uri.parse("package:"+getPackageName())));
                        return;
                    }
                    try{
                        startForegroundService(new Intent(this,OverlayService.class));
                        if(WakeWordService.enabled(this))
                            new Handler(Looper.getMainLooper()).postDelayed(this::startWake,700);
                        statusMessage("Notch ativado.");
                    }catch(Exception ex){
                        view.setChecked(false);
                        statusMessage("Falha no notch: "+ex.getMessage());
                    }
                }else{
                    stopService(new Intent(this,WakeWordService.class));
                    stopService(new Intent(this,OverlayService.class));
                    statusMessage("Notch desativado.");
                }
            });
        settingSwitch(controls,"Ouvir ‘Ei, Home’","Detector local contínuo. O reconhecimento da conversa só abre após Ei Home ou Ok Home.",
            WakeWordService.enabled(this),(view,on)->{
                prefs.edit().putBoolean("wake_enabled",on).apply();
                if(on)startWake();
                else{
                    stopService(new Intent(this,WakeWordService.class));
                    statusMessage("Ativação por voz desligada.");
                }
            });
        settingSwitch(controls,"Mostrar aba de toque","Atalho para abrir o HOME pelo notch.",
            prefs.getBoolean("touch_tab",true),(view,on)->{
                prefs.edit().putBoolean("touch_tab",on).apply();refreshNotch();
            });
        settingSwitch(controls,"Integrar à barra superior","Ajustar a sobreposição ao topo do Android.",
            prefs.getBoolean("edge_mode",true),(view,on)->{
                prefs.edit().putBoolean("edge_mode",on).apply();refreshNotch();
            });
        action(controls,"Ajustar tamanho e posição  ›",false,this::showEditor);
        LinearLayout about=card("Sobre e ferramentas",null);
        add(about,note("HOME · v"+BuildConfig.VERSION_NAME+" · @aqnoeu"),0,12);
        action(about,"↻ Verificar atualizações",false,()->{
            status.setVisibility(View.VISIBLE);
            UpdateHelper.check(this,status);
        });
        action(about,"Downloads oficiais",false,
            ()->startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(DOWNLOAD))));
        action(about,"Mostrar QR Code de download",false,()->showDownloadQr(about));
        LinearLayout device=card("Estado do dispositivo","Consultas sob demanda. Nada é enviado à IA.");
        action(device,"Diagnóstico local do celular",true,
            ()->statusMessage(DeviceHub.overview(this)));
        actions(device,"Bateria",()->statusMessage(DeviceHub.battery(this)),
            "Rede",()->statusMessage(DeviceHub.network(this)));
        actions(device,"Bluetooth",this::showBluetoothStatus,
            "Áudio",()->statusMessage(DeviceHub.audio(this)));
        actions(device,"Memória RAM",()->statusMessage(DeviceHub.memory(this)),
            "Armazenamento",()->statusMessage(DeviceHub.storage()));
        actions(device,"Volume −",()->adjustMediaVolume(false),
            "Volume +",()->adjustMediaVolume(true));
        actions(device,"Configurar Wi-Fi",()->openDeviceSettings(Settings.ACTION_WIFI_SETTINGS),
            "Configurar Bluetooth",()->openDeviceSettings(Settings.ACTION_BLUETOOTH_SETTINGS));
        action(device,"Ver texto copiado (somente agora)",false,
            ()->statusMessage("Texto copiado: "+DeviceHub.clipboard(this)));
        LinearLayout daily=card("Agenda, alarmes e notificações",
            "Ações visíveis e notificações apenas após sua autorização.");
        actions(daily,"Abrir agenda",()->openDeviceIntent(DeviceHub.calendarIntent()),
            "Novo evento",()->openDeviceIntent(DeviceHub.newEventIntent()));
        action(daily,"Compromissos de hoje (com permissão)",false,this::showTodayEvents);
        actions(daily,"Alarmes",()->openDeviceIntent(DeviceHub.alarmsIntent()),
            "Som do sistema",()->openDeviceIntent(DeviceHub.soundSettings()));
        action(daily,"Ver notificações autorizadas",false,this::showNotifications);
        action(about,"Recolher HOME",false,this::finish);
    }

    private void showBluetoothStatus(){
        if(Build.VERSION.SDK_INT>=31 &&
            checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)!=PackageManager.PERMISSION_GRANTED){
            statusMessage("Para consultar Bluetooth, autorize Dispositivos próximos e toque novamente.");
            requestPermissions(new String[]{Manifest.permission.BLUETOOTH_CONNECT},722);
            return;
        }
        statusMessage(DeviceHub.bluetooth(this));
    }
    private void openDeviceIntent(Intent intent){
        try{startActivity(intent);}
        catch(Exception ex){statusMessage("Não há aplicativo compatível para esta ação.");}
    }
    private void adjustMediaVolume(boolean up){
        try{
            android.media.AudioManager manager=(android.media.AudioManager)getSystemService(AUDIO_SERVICE);
            if(manager==null){statusMessage("Controle de áudio indisponível.");return;}
            manager.adjustStreamVolume(android.media.AudioManager.STREAM_MUSIC,
                up?android.media.AudioManager.ADJUST_RAISE:android.media.AudioManager.ADJUST_LOWER,
                android.media.AudioManager.FLAG_SHOW_UI);
            statusMessage(DeviceHub.audio(this));
        }catch(SecurityException ex){statusMessage("O sistema não permitiu alterar o volume.");}
    }
    private void showTodayEvents(){
        if(checkSelfPermission(Manifest.permission.READ_CALENDAR)!=PackageManager.PERMISSION_GRANTED){
            statusMessage("Autorize a leitura da agenda para ver os eventos de hoje. Nenhum evento será enviado à IA.");
            requestPermissions(new String[]{Manifest.permission.READ_CALENDAR},723);
            return;
        }
        statusMessage("Consultando a agenda local...");
        new Thread(()->{
            String answer="Nenhum compromisso encontrado hoje.";
            try{
                java.util.Calendar calendar=java.util.Calendar.getInstance();
                calendar.set(java.util.Calendar.HOUR_OF_DAY,0);
                calendar.set(java.util.Calendar.MINUTE,0);
                calendar.set(java.util.Calendar.SECOND,0);
                calendar.set(java.util.Calendar.MILLISECOND,0);
                long begin=calendar.getTimeInMillis();
                calendar.add(java.util.Calendar.DAY_OF_MONTH,1);
                long end=calendar.getTimeInMillis();
                java.util.ArrayList<String> titles=new java.util.ArrayList<>();
                try(android.database.Cursor cursor=android.provider.CalendarContract.Instances.query(
                    getContentResolver(),
                    new String[]{android.provider.CalendarContract.Instances.TITLE,
                        android.provider.CalendarContract.Instances.BEGIN},begin,end)){
                    if(cursor!=null){
                        while(cursor.moveToNext() && titles.size()<8){
                            String title=cursor.getString(0);
                            long time=cursor.getLong(1);
                            String clock=new java.text.SimpleDateFormat("HH:mm",
                                new java.util.Locale("pt","BR")).format(new Date(time));
                            titles.add(clock+" · "+(title==null?"Sem título":
                                title.substring(0,Math.min(title.length(),90))));
                        }
                    }
                }
                if(!titles.isEmpty())answer="Compromissos de hoje:\n"+String.join("\n",titles);
            }catch(Exception ex){answer="Não consegui ler os compromissos deste aparelho.";}
            final String result=answer;
            runOnUiThread(()->{if(!isFinishing())statusMessage(result);});
        },"home-calendar-read").start();
    }
    private void showNotifications(){
        if(!HomeNotifications.connected()){
            statusMessage("Acesso às notificações desativado. Conceda acesso ao HOME nas configurações do Android.");
            requestInlineConfirm("Acesso às notificações",
                "O HOME poderá ler notificações enquanto o acesso estiver ativo. Só exibiremos conteúdo quando abrir este painel, sem enviar à Groq nem salvar no histórico. Autorizar nas configurações?",
                ()->openDeviceIntent(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)));
            return;
        }
        java.util.List<HomeNotifications.Item> items=HomeNotifications.snapshot();
        clearInline();
        LinearLayout panel=column();
        panel.setBackground(bg(SURFACE,14));
        panel.setPadding(dp(12),dp(12),dp(12),dp(12));
        add(panel,heading("Notificações neste aparelho",16),0,8);
        add(panel,note("Consulta pontual; não armazenamos ou enviamos notificações à IA."),0,9);
        if(items.isEmpty())add(panel,note("Nenhuma notificação de texto disponível."),0,5);
        for(HomeNotifications.Item item:items){
            add(panel,text(item.toString(),13),8,4);
            if(item.reply!=null){
                EditText reply=edit("Resposta para esta notificação",false);
                reply.setSingleLine(false);
                reply.setFilters(new android.text.InputFilter[]{
                    new android.text.InputFilter.LengthFilter(500)});
                add(panel,reply,2,5);
                action(panel,"Responder nesta notificação",false,()->{
                    String message=reply.getText().toString().trim();
                    if(message.isEmpty()){statusMessage("Digite a resposta antes de enviar.");return;}
                    requestInlineConfirm("Enviar resposta",item.source+" — "+item.title+
                        "\nA mensagem será enviada pelo aplicativo da notificação. Confirmar?",
                        ()->statusMessage(HomeNotifications.sendReply(item,message)?
                            "Resposta enviada ao aplicativo.":"Não foi possível responder à notificação."));
                });
            }
        }
        action(panel,"Fechar lista",false,this::clearInline);
        add(inlineHost,panel,2,10);
    }
    /** QR restaura o atalho da versão anterior, sem uma página adicional. */
    private void showDownloadQr(LinearLayout host){
        // A QR square is drawn inside the screen and can be dismissed.
        for(int i=host.getChildCount()-1;i>=0;i--)
            if("home-download-qr".equals(host.getChildAt(i).getTag()))
                host.removeViewAt(i);
        try{
            BitMatrix matrix=new MultiFormatWriter().encode(DOWNLOAD,BarcodeFormat.QR_CODE,260,260);
            Bitmap bitmap=Bitmap.createBitmap(260,260,Bitmap.Config.ARGB_8888);
            for(int y=0;y<260;y++)for(int x=0;x<260;x++)
                bitmap.setPixel(x,y,matrix.get(x,y)?Color.BLACK:WHITE);
            LinearLayout panel=column();
            panel.setTag("home-download-qr");
            panel.setPadding(dp(8),dp(8),dp(8),dp(8));
            panel.setBackground(bg(WHITE,13));
            ImageView qr=new ImageView(this);
            qr.setImageBitmap(bitmap);
            qr.setContentDescription("QR Code dos downloads oficiais do HOME");
            qr.setScaleType(ImageView.ScaleType.FIT_CENTER);
            panel.addView(qr,new LinearLayout.LayoutParams(-1,dp(260)));
            add(panel,text("Escaneie para abrir os downloads do HOME.",12,BG,false),8,8);
            action(panel,"Fechar QR Code",false,()->host.removeView(panel));
            add(host,panel,8,9);
        }catch(Exception ex){statusMessage("Não foi possível gerar QR Code: "+ex.getMessage());}
    }

    /** Offline device actions never require Groq or network connectivity. */
    private void openDeviceSettings(String action){
        try{startActivity(new Intent(action));}
        catch(Exception ex){statusMessage("Configuração não disponível neste aparelho.");}
    }
    private String readBatteryStatus(){
        Intent state=registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if(state==null)return "Não consegui consultar a bateria.";
        int level=state.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
        int scale=state.getIntExtra(BatteryManager.EXTRA_SCALE,-1);
        if(level<0||scale<=0)return "Não consegui consultar a bateria.";
        int percent=Math.round(100f*level/scale);
        int plug=state.getIntExtra(BatteryManager.EXTRA_PLUGGED,0);
        return "Bateria em "+percent+"%"+(plug!=0?" · carregando.":".");
    }
    private boolean handleLocalCommand(String query){return handleLocalCommand(query,false);}
    private boolean handleLocalCommand(String query,boolean speak){
        HomeLocalCommands.Result result=HomeLocalCommands.resolve(this,query);
        if(result==null)return false;
        String answer=result.answer;
        String setting=result.setting;
        try{
            HomeChatStore store=HomeChatStore.get(this);
            store.add("user",query);
            store.add("assistant",answer);
            refreshChat();
            if(setting!=null)openDeviceSettings(setting);
            // A spoken request must get a spoken answer; text-only requests stay silent.
            if(speak)speakAnswer(answer);
            return true;
        }catch(Exception ex){
            statusMessage("Não consegui salvar a resposta local.");
            if(speak)resumeWake();
            return true;
        }
    }

    private void settingsVoice(){
        android.content.SharedPreferences prefs=getSharedPreferences("home",MODE_PRIVATE);
        LinearLayout response=card("Voz e microfone","A conversa continua funcionando em texto.");
        settingSwitch(response,"Responder com voz","Usar Faber quando instalada.",
            prefs.getBoolean("voice_replies",true),(view,on)->
                prefs.edit().putBoolean("voice_replies",on).apply());
        TextView voiceState=note(FaberOffline.isInstalled(this)?
            "✓ Faber instalada":"Voz offline ainda não instalada.");
        add(response,voiceState,0,8);
        action(response,FaberOffline.isInstalled(this)?"Testar voz Faber":"Instalar Faber",false,()->{
            if(FaberOffline.isInstalled(this)){
                FaberOffline.speak(this,"Olá! Eu sou o HOME.",voiceState::setText);
            }else requestInlineConfirm("Instalar Faber",
                "O download inicial requer aproximadamente 67 MB.",()->{
                    FaberOffline.installAsync(this,voiceState::setText);
                });
        });
        action(response,"Testar microfone",false,()->{openVoiceListening();});
        LinearLayout enrollment=card("Reconhecimento personalizado",
            "Cadastre Ei Home, Ok Home e Home, depois teste cada chamada junto de uma função.");
        add(enrollment,note(VoiceEnrollment.summary(this)),0,9);
        action(enrollment,"Cadastrar minha voz",true,this::showVoiceEnrollment);
        settingSwitch(enrollment,"Aprendizado por correções",
            "Registrar variantes confirmadas no próprio aparelho.",
            VoiceEnrollment.corrections(this),(view,on)->VoiceEnrollment.setCorrections(this,on));
        action(enrollment,"Configurar ativação contínua",false,()->showSettings("Geral"));

        LinearLayout ia=card("Inteligência artificial",null);
        TextView groq=note(HomeGroq.connected(this)?
            "● Groq conectada":"● Groq desconectada");
        groq.setTextColor(HomeGroq.connected(this)?GREEN:MUTED);
        add(ia,groq,0,8);
        LinearLayout groqSettingsHost=column();
        add(ia,groqSettingsHost,0,8);
        action(ia,"Gerenciar chave Groq",false,()->showConnectionSettings(groq,groqSettingsHost));
        LinearLayout diagnostics=card("Diagnóstico de voz",null);
        TextView report=note("Verifique a instalação e o estado da Faber.");
        add(diagnostics,report,0,9);
        action(diagnostics,"Ver diagnóstico",false,()->
            report.setText(FaberOffline.diagnostic(this)));
        action(diagnostics,"Copiar diagnóstico",false,()->{
            String value=FaberOffline.diagnostic(this);
            ((ClipboardManager)getSystemService(CLIPBOARD_SERVICE))
                .setPrimaryClip(ClipData.newPlainText("Diagnóstico HOME",value));
            statusMessage("Diagnóstico copiado.");
        });
    }

    /** Two-row, paged, selectable gallery. Hidden faces can be restored in Appearance. */
    private void addExpressionPicker(LinearLayout face,EyesView eyes,
                                     android.content.SharedPreferences prefs){
        eyes.setExpressionPreview(true);
        final int columns=3, perPage=6;
        final int[] currentPage={0};
        LinearLayout selector=column();
        GridLayout grid=new GridLayout(this);
        grid.setColumnCount(columns);
        selector.addView(grid,new LinearLayout.LayoutParams(-1,-2));
        LinearLayout pager=new LinearLayout(this);
        pager.setGravity(Gravity.CENTER_VERTICAL);
        Button previous=button("‹",false,()->{});
        Button next=button("›",false,()->{});
        TextView pageText=text("",12,MUTED,true);
        pageText.setGravity(Gravity.CENTER);
        pager.addView(previous,new LinearLayout.LayoutParams(dp(48),dp(40)));
        pager.addView(pageText,new LinearLayout.LayoutParams(0,dp(40),1));
        pager.addView(next,new LinearLayout.LayoutParams(dp(48),dp(40)));
        selector.addView(pager);
        Runnable[] redraw=new Runnable[1];
        redraw[0]=()->{
            java.util.ArrayList<Integer> visible=new java.util.ArrayList<>();
            for(int i=0;i<EyesView.EXPRESSION_KEYS.length;i++){
                if(HomeEmotion.enabled(this,EyesView.EXPRESSION_KEYS[i]))visible.add(i);
            }
            int pageCount=Math.max(1,(visible.size()+perPage-1)/perPage);
            currentPage[0]=Math.min(currentPage[0],pageCount-1);
            grid.removeAllViews();
            int selected=prefs.getInt("mood",0);
            int first=currentPage[0]*perPage;
            for(int position=0;position<perPage && first+position<visible.size();position++){
                final int index=visible.get(first+position);
                Button b=button(EyesView.EXPRESSION_LABELS[index],false,()->{
                    prefs.edit().putInt("mood",index).putBoolean("expression_fixed",true).apply();
                    eyes.setMood(index);
                    if(Settings.canDrawOverlays(this))refreshNotch();
                    showStatus("Expressão: "+EyesView.EXPRESSION_LABELS[index]);
                    if(status!=null)status.setVisibility(View.VISIBLE);
                    redraw[0].run();
                });
                b.setOnLongClickListener(v->{
                    // Hide, never destroy a built-in face. One visible fallback is required.
                    int activeCount=0;
                    for(String key:EyesView.EXPRESSION_KEYS)if(HomeEmotion.enabled(this,key))activeCount++;
                    if(activeCount<=1){statusMessage("Mantenha pelo menos uma expressão ativa.");return true;}
                    HomeEmotion.setEnabled(this,EyesView.EXPRESSION_KEYS[index],false);
                    if(prefs.getInt("mood",0)==index){
                        int replacement=0;
                        for(int candidate=0;candidate<EyesView.EXPRESSION_KEYS.length;candidate++){
                            if(HomeEmotion.enabled(this,EyesView.EXPRESSION_KEYS[candidate])){replacement=candidate;break;}
                        }
                        prefs.edit().putInt("mood",replacement).apply();
                        eyes.setMood(replacement);
                    }
                    if(Settings.canDrawOverlays(this))refreshNotch();
                    statusMessage(EyesView.EXPRESSION_LABELS[index]+" ocultada; restaure em Gerenciar expressões.");
                    redraw[0].run();
                    return true;
                });
                b.setContentDescription(EyesView.EXPRESSION_LABELS[index]+
                    ". Toque para selecionar; mantenha pressionado para ocultar.");
                b.setTextSize(11);
                b.setSingleLine(true);
                b.setAllCaps(false);
                b.setPadding(dp(3),0,dp(3),0);
                b.setBackground(bg(index==selected?BLUE:RAISED,10));
                GridLayout.LayoutParams lp=new GridLayout.LayoutParams(
                    GridLayout.spec(position/columns),GridLayout.spec(position%columns,1f));
                lp.width=0;lp.height=dp(43);
                lp.setMargins(dp(2),dp(3),dp(2),dp(3));
                grid.addView(b,lp);
            }
            pageText.setText((currentPage[0]+1)+" / "+pageCount);
            previous.setEnabled(currentPage[0]>0);
            next.setEnabled(currentPage[0]<pageCount-1);
        };
        previous.setOnClickListener(v->{if(currentPage[0]>0){currentPage[0]--;redraw[0].run();}});
        next.setOnClickListener(v->{currentPage[0]++;redraw[0].run();});
        redraw[0].run();
        face.addView(selector);
        action(face,"Voltar às expressões automáticas",false,()->{
            prefs.edit().putBoolean("expression_fixed",false).apply();
            if(Settings.canDrawOverlays(this))refreshNotch();
            statusMessage("Expressões automáticas reativadas.");
        });
        add(face,note("Toque para testar. Pressione e segure para ocultar; restaure em Gerenciar expressões."),4,0);
    }

    private void addEmotionSwitch(LinearLayout section,String label,String key){
        LinearLayout line=new LinearLayout(this);
        line.setOrientation(LinearLayout.HORIZONTAL);
        line.setGravity(Gravity.CENTER_VERTICAL);
        Switch toggle=new Switch(this);
        toggle.setText(label);
        toggle.setTextColor(WHITE);
        toggle.setTextSize(12);
        toggle.setChecked(HomeEmotion.enabled(this,key));
        toggle.setOnCheckedChangeListener((button,checked)->{
            if(!checked && "neutro".equals(key)){
                // Neutral is a built-in render fallback; disabling it is still allowed.
            }
            if(!checked && isNativeExpression(key)){
                int remaining=0;
                for(String value:EyesView.EXPRESSION_KEYS)
                    if(!value.equals(key) && HomeEmotion.enabled(this,value))remaining++;
                if(remaining==0){
                    toggle.setChecked(true);
                    statusMessage("Mantenha pelo menos uma expressão ativa.");
                    return;
                }
            }
            HomeEmotion.setEnabled(this,key,checked);
            if(!checked)ensureValidSelectedExpression();
            if(Settings.canDrawOverlays(this))refreshNotch();
        });
        line.addView(toggle,new LinearLayout.LayoutParams(0,dp(48),1));
        Button hide=button("✕",false,()->{
            if(!toggle.isChecked()){
                statusMessage(label+" já está oculta.");
                return;
            }
            toggle.setChecked(false); // uses the same validated path as the switch
            if(!toggle.isChecked())statusMessage(label+" ocultada. Restaure pelo interruptor.");
        });
        hide.setContentDescription("Ocultar expressão "+label);
        line.addView(hide,new LinearLayout.LayoutParams(dp(44),dp(40)));
        add(section,line,0,3);
    }
    private boolean isNativeExpression(String key){
        for(String value:EyesView.EXPRESSION_KEYS)if(value.equals(key))return true;
        return false;
    }
    private void ensureValidSelectedExpression(){
        android.content.SharedPreferences prefs=getSharedPreferences("home",MODE_PRIVATE);
        int selected=prefs.getInt("mood",0);
        if(selected>=0 && selected<EyesView.EXPRESSION_KEYS.length &&
            HomeEmotion.enabled(this,EyesView.EXPRESSION_KEYS[selected]))return;
        for(int index=0;index<EyesView.EXPRESSION_KEYS.length;index++){
            if(HomeEmotion.enabled(this,EyesView.EXPRESSION_KEYS[index])){
                prefs.edit().putInt("mood",index).apply();
                return;
            }
        }
    }
    private void settingsAppearance(){
        android.content.SharedPreferences prefs=getSharedPreferences("home",MODE_PRIVATE);
        LinearLayout face=card("Catálogo de expressões","Toque para visualizar e usar no notch. Duas linhas, sem rolagem lateral.");
        EyesView eyes=new EyesView(this);
        eyes.setExpressionPreview(true);eyes.setMood(prefs.getInt("mood",0));
        eyes.setEyeGap(prefs.getInt("eye_gap",9));
        eyes.setBackground(bg(BG,18));
        LinearLayout.LayoutParams preview=new LinearLayout.LayoutParams(-1,dp(84));
        preview.bottomMargin=dp(10);
        face.addView(eyes,preview);
        addExpressionPicker(face,eyes,prefs);
        LinearLayout manager=card("Administrar expressões",
            "Ative ou desative cada reação do HOME. A lixeira oculta expressões nativas sem apagá-las definitivamente.");
        manager.setVisibility(View.GONE);
        action(face,"Gerenciar expressões e reações  ›",false,()->
            manager.setVisibility(manager.getVisibility()==View.VISIBLE?View.GONE:View.VISIBLE));
        String[] nativeLabels=EyesView.EXPRESSION_LABELS;
        String[] nativeKeys=EyesView.EXPRESSION_KEYS;
        for(int i=0;i<nativeLabels.length;i++){
            final String key=nativeKeys[i];
            final String label=nativeLabels[i];
            addEmotionSwitch(manager,label,key);
        }
        String[] situationalLabels={"Carregando","Bateria fraca","Economia de energia",
            "Durante a conversa (verde)","Ouvindo (verde)","Falando"};
        String[] situationalKeys={"carregando","bateria_baixa","economia",
            "conversa","escutando","falando"};
        for(int i=0;i<situationalKeys.length;i++)
            addEmotionSwitch(manager,situationalLabels[i],situationalKeys[i]);
        action(manager,"Restaurar todas as expressões",false,()->{
            for(String key:nativeKeys)HomeEmotion.setEnabled(this,key,true);
            for(String key:situationalKeys)HomeEmotion.setEnabled(this,key,true);
            if(Settings.canDrawOverlays(this))refreshNotch();
            showSettings("Aparência");
        });
        LinearLayout setup=card("Posição e aparência",null);
        action(setup,"Ajustar notch e distância dos olhos  ›",false,this::showEditor);
        add(setup,note("A identidade dos olhos é preservada conforme o Manual de Marca HOME."),6,0);
    }
    /** A real chat layout: independent message scroll and a fixed input dock. */
    private void assistantPage(){
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        LinearLayout shell=column();
        shell.setBackgroundColor(BG);
        shell.setFocusableInTouchMode(true);
        final int horizontal=dp(16);
        shell.setPadding(horizontal,dp(8),horizontal,dp(8));
        shell.setOnApplyWindowInsetsListener((view,insets)->{
            if(Build.VERSION.SDK_INT>=30){
                android.graphics.Insets bars=insets.getInsets(
                    WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());
                android.graphics.Insets keyboard=insets.getInsets(WindowInsets.Type.ime());
                shell.setPadding(horizontal,bars.top+dp(6),horizontal,
                    Math.max(bars.bottom,keyboard.bottom)+dp(6));
            }
            return insets;
        });
        setContentView(shell);
        shell.requestApplyInsets();

        LinearLayout top=new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        ImageView logo=new ImageView(this);
        logo.setImageResource(R.drawable.home_header_eyes);
        logo.setBackground(null);
        logo.setScaleType(ImageView.ScaleType.FIT_CENTER);
        logo.setContentDescription("Olhos oficiais do HOME");
        top.addView(logo,new LinearLayout.LayoutParams(dp(34),dp(40)));
        LinearLayout titleBox=column();
        TextView label=heading("HOME",18);
        add(titleBox,label,0,2);
        TextView state=text(HomeGroq.connected(this)?"● Conectado":"● Sem conexão",11,
            HomeGroq.connected(this)?GREEN:MUTED,false);
        state.setSingleLine(true);
        state.setEllipsize(android.text.TextUtils.TruncateAt.END);
        add(titleBox,state,0,0);
        LinearLayout.LayoutParams titleParams=new LinearLayout.LayoutParams(0,-2,1);
        titleParams.leftMargin=dp(8);
        top.addView(titleBox,titleParams);
        Button newChat=button("+",false,()->{
            HomeChatStore.get(this).newChat();
            refreshChat();
        });
        newChat.setContentDescription("Nova conversa");
        newChat.setTextSize(20);
        Button refresh=button("↻",false,()->{
            status.setVisibility(View.VISIBLE);
            UpdateHelper.check(this,status);
        });
        refresh.setTextSize(19);
        refresh.setContentDescription("Verificar atualizações");
        top.addView(refresh,new LinearLayout.LayoutParams(dp(40),dp(44)));
        Button settings=button("⚙",false,()->showSettings("Geral"));
        settings.setTextSize(19);
        settings.setContentDescription("Configurações");
        top.addView(settings,new LinearLayout.LayoutParams(dp(40),dp(44)));
        top.addView(newChat,new LinearLayout.LayoutParams(dp(40),dp(44)));
        shell.addView(top,new LinearLayout.LayoutParams(-1,-2));

        // Current conversation is a discreet caption; history already has a nav destination.
        chatTitle=note("Conversa atual");
        chatTitle.setTextSize(11);
        chatTitle.setSingleLine(true);
        chatTitle.setEllipsize(android.text.TextUtils.TruncateAt.END);
        chatTitle.setGravity(Gravity.CENTER_VERTICAL);
        shell.addView(chatTitle,new LinearLayout.LayoutParams(-1,dp(28)));

        View rule=new View(this);
        rule.setBackgroundColor(LINE);
        LinearLayout.LayoutParams ruleParams=new LinearLayout.LayoutParams(-1,dp(1));
        ruleParams.bottomMargin=dp(6);
        shell.addView(rule,ruleParams);

        chatScroll=new ScrollView(this);
        chatScroll.setFillViewport(true);
        chatScroll.setClipToPadding(false);
        chatScroll.setVerticalScrollBarEnabled(true);
        chatMessages=column();
        chatMessages.setPadding(dp(2),dp(7),dp(2),dp(8));
        chatScroll.addView(chatMessages,new ScrollView.LayoutParams(-1,-2));
        shell.addView(chatScroll,new LinearLayout.LayoutParams(-1,0,1f));

        status=note("");
        status.setVisibility(View.GONE);
        status.setMaxLines(3);
        status.setEllipsize(android.text.TextUtils.TruncateAt.END);
        LinearLayout.LayoutParams stateParams=new LinearLayout.LayoutParams(-1,-2);
        stateParams.topMargin=dp(3);stateParams.bottomMargin=dp(4);
        shell.addView(status,stateParams);

        LinearLayout dock=new LinearLayout(this);
        dock.setOrientation(LinearLayout.HORIZONTAL);
        dock.setGravity(Gravity.BOTTOM|Gravity.CENTER_VERTICAL);
        dock.setBackground(bg(RAISED,18));
        dock.setPadding(dp(4),dp(3),dp(4),dp(3));

        Button mic=button("◉",false,()->{
            openVoiceListening();
        });
        mic.setTextSize(20);
        mic.setContentDescription("Falar com o Home");
        mic.setBackgroundColor(Color.TRANSPARENT);
        dock.addView(mic,new LinearLayout.LayoutParams(dp(40),dp(44)));

        chatInput=new EditText(this);
        chatInput.setHint("Mensagem para o HOME…");
        chatInput.setHintTextColor(MUTED);
        chatInput.setTextColor(WHITE);
        chatInput.setTextSize(14);
        chatInput.setIncludeFontPadding(false);
        chatInput.setSingleLine(false);
        chatInput.setMinLines(1);chatInput.setMaxLines(5);
        chatInput.setGravity(Gravity.CENTER_VERTICAL|Gravity.START);
        chatInput.setInputType(InputType.TYPE_CLASS_TEXT|
            InputType.TYPE_TEXT_FLAG_CAP_SENTENCES|InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        chatInput.setPadding(dp(5),dp(7),dp(5),dp(7));
        chatInput.setBackgroundColor(Color.TRANSPARENT);
        chatInput.setFilters(new android.text.InputFilter[]{
            new android.text.InputFilter.LengthFilter(750)});
        dock.addView(chatInput,new LinearLayout.LayoutParams(0,-2,1f));

        Button send=button("➤",true,()->sendChatMessage());
        send.setTextSize(18);
        send.setContentDescription("Enviar mensagem");
        LinearLayout.LayoutParams sendParams=new LinearLayout.LayoutParams(dp(42),dp(42));
        sendParams.leftMargin=dp(3);
        dock.addView(send,sendParams);
        LinearLayout.LayoutParams dockParams=new LinearLayout.LayoutParams(-1,-2);
        dockParams.topMargin=dp(4);
        shell.addView(dock,dockParams);

        inlineHost=column();
        shell.addView(inlineHost,new LinearLayout.LayoutParams(-1,-2));
        LinearLayout footer=bottomNavigation("assistant");
        LinearLayout.LayoutParams footerParams=new LinearLayout.LayoutParams(-1,dp(50));
        footerParams.topMargin=dp(4);
        shell.addView(footer,footerParams);
        refreshChat();
        shell.requestFocus();

        // Groq credentials are managed in Settings > Voz / IA, not in the chat header.
    }

    private void showConnectionSettings(TextView state,LinearLayout host){
        host.removeAllViews();
        LinearLayout panel=column();
        panel.setPadding(dp(12),dp(12),dp(12),dp(12));
        panel.setBackground(bg(SURFACE,14));
        add(panel,heading("Conexão Groq",16),0,6);
        EditText secret=edit("Chave Groq · gsk_…",true);
        add(panel,secret,0,7);
        action(panel,"Salvar chave",true,()->{
            try{
                String entered=secret.getText().toString().trim();
                HomeGroq.connect(this,entered);
                secret.setText("");
                backupGroqToAccount(entered,state);
                state.setText("● Groq conectada");
                state.setTextColor(GREEN);
                host.removeAllViews();
                statusMessage("Conexão Groq salva.");
            }catch(Exception e){statusMessage("Não foi possível conectar: "+e.getMessage());}
        });
        action(panel,"Restaurar da Conta HOME",false,()->{
            if(unifiedAccount==null)unifiedAccount=new HomeHubAccount(this);
            final HomeHubAccount account=unifiedAccount;
            new Thread(()->{
                try{
                    if(!account.connected()&&!account.resume())throw new IllegalStateException("Entre primeiro em Conta HOME.");
                    String stored=account.restoreGroqKey();
                    if(stored==null)throw new IllegalStateException("A conta não possui chave salva. Cadastre uma vez.");
                    HomeGroq.connect(this,stored);
                    runOnUiThread(()->{state.setText("● Groq conectada");state.setTextColor(GREEN);host.removeAllViews();});
                }catch(Exception e){runOnUiThread(()->statusMessage(e.getMessage()));}
            },"home-groq-manual-restore").start();
        });
        action(panel,"Desconectar neste aparelho",false,()->{
            HomeGroq.disconnect(this);
            state.setText("● Groq desconectada neste aparelho");
            state.setTextColor(MUTED);
            statusMessage("Chave local desconectada. Backup da conta preservado.");
        });
        action(panel,"Apagar também da Conta HOME",false,()->{
            host.removeAllViews();
            add(host,note("Confirma apagar a chave Groq da Conta HOME? A exclusão não pode ser desfeita."),0,8);
            action(host,"Confirmar exclusão",true,()->{
                if(unifiedAccount==null)unifiedAccount=new HomeHubAccount(this);
                final HomeHubAccount account=unifiedAccount;
                new Thread(()->{
                    try{
                        if(!account.connected()&&!account.resume())throw new IllegalStateException("Entre na Conta HOME.");
                        account.forgetGroqKey();
                        HomeGroq.disconnect(this);
                        runOnUiThread(()->{state.setText("● Groq desconectada");state.setTextColor(MUTED);host.removeAllViews();});
                    }catch(Exception e){runOnUiThread(()->statusMessage("Não foi possível apagar: "+e.getMessage()));}
                },"home-groq-forget").start();
            });
            action(host,"Cancelar",false,()->showConnectionSettings(state,host));
        });
        action(panel,"Fechar",false,host::removeAllViews);
        add(host,panel,0,5);
    }

    private void sendChatMessage(){
        if(chatInput==null)return;
        String q=chatInput.getText().toString().trim();
        if(q.isEmpty())return;
        if(handleLocalCommand(q)){chatInput.setText("");return;}
        if(!HomeGroq.connected(this)){
            statusMessage("Conecte a Groq tocando no indicador do cabeçalho.");
            return;
        }
        chatInput.setText("");
        statusMessage("HOME está pensando…");
        pauseWake();
        refreshChat();
        askHome(q,status);
    }
    private void bubble(String role,String message){
        if(chatMessages==null)return;
        boolean user="user".equals(role);
        LinearLayout line=new LinearLayout(this);
        line.setOrientation(LinearLayout.HORIZONTAL);
        line.setGravity(user?Gravity.RIGHT:Gravity.LEFT);
        TextView body=text(message,14,WHITE,false);
        body.setMaxWidth(dp(Math.min(310,
            Math.round(getResources().getConfiguration().screenWidthDp*0.82f))));
        body.setBackground(bg(user?BLUE:RAISED,14));
        body.setPadding(dp(12),dp(9),dp(12),dp(9));
        LinearLayout.LayoutParams bodySize=new LinearLayout.LayoutParams(-2,-2);
        bodySize.leftMargin=user?dp(27):0;
        bodySize.rightMargin=user?0:dp(27);
        line.addView(body,bodySize);
        add(chatMessages,line,0,8);
    }
    private void refreshChat(){
        if(chatMessages==null||!"assistant".equals(currentPage))return;
        HomeChatStore store=HomeChatStore.get(this);
        String id=store.ensureActive();
        String title="Nova conversa";
        for(JSONObject c:store.conversations()){
            if(id.equals(c.optString("id"))){title=c.optString("title","Conversa");break;}
        }
        if(chatTitle!=null)chatTitle.setText(title);
        chatMessages.removeAllViews();
        JSONArray messages=store.messages();
        for(int i=0;i<messages.length();i++){
            JSONObject m=messages.optJSONObject(i);
            if(m!=null)bubble(m.optString("role"),m.optString("text"));
        }
        if(messages.length()==0)add(chatMessages,note("Comece uma conversa com o HOME."),0,10);
        if(chatScroll!=null)chatScroll.post(()->chatScroll.fullScroll(View.FOCUS_DOWN));
    }
    private void renderChatList(){
        if(chatPicker==null)return;
        chatPicker.removeAllViews();
        HomeChatStore store=HomeChatStore.get(this);
        for(JSONObject entry:store.conversations()){
            final String id=entry.optString("id");
            String name=entry.optString("title","Conversa");
            String date=DateFormat.getDateTimeInstance(DateFormat.SHORT,DateFormat.SHORT)
                .format(new Date(entry.optLong("updated")));
            LinearLayout item=new LinearLayout(this);
            item.setOrientation(LinearLayout.HORIZONTAL);
            item.setGravity(Gravity.CENTER_VERTICAL);
            item.setPadding(dp(4),dp(4),dp(4),dp(4));
            LinearLayout details=column();
            TextView nameText=text(name,14,WHITE,true);
            nameText.setMaxLines(1);
            nameText.setEllipsize(android.text.TextUtils.TruncateAt.END);
            add(details,nameText,0,4);
            add(details,note(date),0,0);
            details.setPadding(dp(8),dp(9),dp(8),dp(9));
            details.setOnClickListener(v->{
                store.select(id);
                showPage("assistant");
            });
            item.addView(details,new LinearLayout.LayoutParams(0,-2,1f));
            Button delete=button("×",false,()->requestInlineConfirm(
                "Excluir conversa","Deseja excluir esta conversa deste aparelho?",()->{
                    store.delete(id);renderChatList();refreshChat();
                }));
            delete.setTextSize(21);
            delete.setContentDescription("Excluir "+name);
            item.addView(delete,new LinearLayout.LayoutParams(dp(48),dp(48)));
            add(chatPicker,item,0,4);
            View divider=new View(this);
            divider.setBackgroundColor(LINE);
            chatPicker.addView(divider,new LinearLayout.LayoutParams(-1,dp(1)));
        }
    }
    private void askHome(String question,TextView response){
        if(!HomeGroq.connected(this)){
            if(response!=null){
                response.setText("Conecte a Groq na seção Assistente para fazer perguntas.");
                resumeWake();
            }else{
                // Pergunta por voz: mostra o aviso na própria conversa em vez de só na barra de status.
                reportVoiceFailure(question,"Conecte a Groq na seção Assistente para eu responder perguntas por voz.");
            }
            return;
        }
        HomeEmotion.fromGroq("neutro");
        HomeGroq.ask(this,question,new HomeGroq.Callback(){
            @Override public void onEmotion(String emotion){HomeEmotion.fromGroq(emotion);}
            @Override public void onAnswer(String answer){
                if(response!=null){response.setText("");response.setVisibility(View.GONE);}
                refreshChat();
                if(FaberOffline.isInstalled(MainActivity.this))speakAnswer(answer);
                else {resumeWake();statusMessage("Resposta pronta em texto. Instale Faber em Voz para ouvir.");}
            }
            @Override public void onError(String message){
                resumeWake();
                refreshChat();
                if(response!=null){response.setVisibility(View.VISIBLE);response.setText(message);}
                statusMessage(message);
            }
        });
    }
    private void voicePage(){
        LinearLayout voice=card("Faber · português brasileiro",
            "Uma voz, no PC e no celular. Síntese local e gratuita.");
        TextView voiceState=note(FaberOffline.isInstalled(this)?
            "✓ Voz instalada neste aparelho":"Voz não instalada · download inicial de aproximadamente 67 MB");
        if(FaberOffline.isInstalled(this))voiceState.setTextColor(GREEN);
        add(voice,voiceState,0,11);
        action(voice,FaberOffline.isInstalled(this)?"✓ Faber instalada":"Instalar voz Faber",false,()->{
            if(FaberOffline.isInstalled(this)){success(voiceState,"Voz já instalada");return;}
            requestInlineConfirm("Instalar Faber","Download gratuito de aproximadamente 67 MB, com 250 MB temporários disponíveis. Depois, a voz funciona offline.",()->{
                voiceState.setText("Preparando instalação…");
                FaberOffline.installAsync(this,voiceState::setText);
            });
        });
        action(voice,"▶ Testar Faber",true,()->FaberOffline.speak(this,
            "Olá! Eu sou o HOME. Esta é minha voz no celular.",
            voiceState::setText));
        LinearLayout microphone=card("Microfone","Fale com o HOME e receba uma resposta formulada pela Groq.");
        action(microphone,"◉ Perguntar por voz",true,()->{openVoiceListening();});
        action(microphone,"Abrir Assistente",false,()->showPage("assistant"));
        LinearLayout diagnostics=card("Diagnóstico","Informações de instalação, modelo e reprodução, sem janelas sobrepostas.");
        TextView report=note("Toque para exibir as informações técnicas da Faber.");
        add(diagnostics,report,0,12);
        actions(diagnostics,"Ver diagnóstico",()->report.setText(FaberOffline.diagnostic(this)),
            "Copiar dados",()->{
                String value=FaberOffline.diagnostic(this);
                ((ClipboardManager)getSystemService(CLIPBOARD_SERVICE))
                    .setPrimaryClip(ClipData.newPlainText("Diagnóstico Faber",value));
                report.setText("Diagnóstico copiado.");
            });
    }
    /** Two phases: three wake calls, then three wake + offline-function examples. */
    private void showVoiceEnrollment(){
        initScreen("voice_enrollment","Cadastro de frases de ativação e testes de chamada + função.");
        LinearLayout box=card("Personalizar reconhecimento","As frases reconhecidas e suas correções ficam salvas neste aparelho. O treinamento não cria uma identificação biométrica de locutor.");
        TextView info=note(VoiceEnrollment.summary(this));
        add(box,info,0,12);
        int step=VoiceEnrollment.step(this);
        if(step<VoiceEnrollment.count()){
            add(box,heading("Diga: "+VoiceEnrollment.prompt(step),19),0,12);
            action(box,"Gravar e verificar frase",true,()->{
                pauseWake();
                Intent recognition=new Intent(android.speech.RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
                recognition.putExtra(android.speech.RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    android.speech.RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
                recognition.putExtra(android.speech.RecognizerIntent.EXTRA_LANGUAGE,"pt-BR");
                recognition.putExtra(android.speech.RecognizerIntent.EXTRA_PREFER_OFFLINE,true);
                recognition.putExtra(android.speech.RecognizerIntent.EXTRA_PROMPT,VoiceEnrollment.prompt(VoiceEnrollment.step(this)));
                try{startActivityForResult(recognition,VOICE_ENROLL_REQUEST);}
                catch(Exception ex){resumeWake();statusMessage("Reconhecimento indisponível no aparelho. Instale um serviço de fala compatível.");}
            });
        }else{
            add(box,note("✓ Todos os seis testes foram confirmados. A ativação offline continua sendo feita pelo detector Vosk."),0,12);
        }
        settingSwitch(box,"Aprendizado por correções",
            "Guardar transcrições corrigidas para ajustar variantes de ativação. Não treina um modelo acústico automaticamente.",
            VoiceEnrollment.corrections(this),(view,on)->VoiceEnrollment.setCorrections(this,on));
        action(box,"Reiniciar cadastro e apagar correções",false,()->requestInlineConfirm(
            "Apagar cadastro de voz","Isso excluirá os testes e as variantes corrigidas armazenadas neste aparelho.",()->{
                VoiceEnrollment.reset(this);showVoiceEnrollment();
            }));
        action(box,"Voltar a Voz / IA",false,()->showSettings("Voz / IA"));
        add(box,note("A captura do exercício usa o serviço de reconhecimento de fala instalado no Android, com preferência offline. O Android pode usar rede conforme o serviço escolhido. O detector normal do Home permanece Vosk local."),6,0);
    }
    private String enrollmentOfflineResult(int step){
        java.util.Locale pt=new java.util.Locale("pt","BR");
        if(step==3)return "Agora são "+new java.text.SimpleDateFormat("HH:mm",pt).format(new java.util.Date())+".";
        if(step==4)return "Hoje é "+new java.text.SimpleDateFormat("dd/MM/yyyy",pt).format(new java.util.Date())+".";
        if(step==5)return DeviceHub.battery(this);
        return "";
    }
    private void finishEnrollmentCapture(int resultCode,Intent data){
        resumeWake();
        if(resultCode!=RESULT_OK||data==null){
            showVoiceEnrollment();statusMessage("Gravação cancelada. Nenhum teste foi registrado.");return;
        }
        java.util.ArrayList<String> found=data.getStringArrayListExtra(android.speech.RecognizerIntent.EXTRA_RESULTS);
        if(found==null||found.isEmpty()){
            showVoiceEnrollment();statusMessage("Nenhuma frase reconhecida. Tente novamente.");return;
        }
        int step=VoiceEnrollment.step(this);
        if(step>=VoiceEnrollment.count()){showVoiceEnrollment();return;}
        String heard=found.get(0);
        boolean matched=false;
        for(String alternative:found)if(VoiceEnrollment.matches(step,alternative)){heard=alternative;matched=true;break;}
        if(matched){
            VoiceEnrollment.accept(this,heard,false);
            showVoiceEnrollment();statusMessage("✓ Reconhecido: "+heard+(step>=3?"\nFunção offline executada: "+enrollmentOfflineResult(step):""));return;
        }
        final String captured=heard;
        showVoiceEnrollment();
        LinearLayout correction=column();
        correction.setPadding(dp(14),dp(14),dp(14),dp(14));
        correction.setBackground(bg(RAISED,13));
        add(correction,heading("Conferir reconhecimento",16),0,8);
        add(correction,note("O aparelho entendeu: "+captured),0,6);
        add(correction,note("Você realmente falou: "+VoiceEnrollment.prompt(step)+"?"),0,12);
        actions(correction,"Sim, corrigir",()->{
            if(!VoiceEnrollment.corrections(this)){
                statusMessage("Ative o aprendizado por correções para registrar esta amostra.");return;
            }
            VoiceEnrollment.accept(this,captured,true);
            showVoiceEnrollment();
            statusMessage("Correção confirmada."+(step>=3?"\nFunção offline executada: "+enrollmentOfflineResult(step):" O detector poderá aceitar a variante; o modelo acústico não foi treinado."));
        },"Não, repetir",this::showVoiceEnrollment);
        add(inlineHost,correction,0,12);
    }
    private void interactionPage(){
        LinearLayout box=card("Notch do HOME","Controle a sobreposição com ações claras e estados visíveis.");
        action(box,"Ativar Notch",true,()->{
            if(!Settings.canDrawOverlays(this)){
                statusMessage("Autorize a sobreposição nas configurações do Android e volte aqui.");
                startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:"+getPackageName())));return;
            }
            if(Build.VERSION.SDK_INT>=33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)
                requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},1);
            try{
                startForegroundService(new Intent(this,OverlayService.class));
                statusMessage("✓ Notch ativado.");
                if(WakeWordService.enabled(this))new Handler(Looper.getMainLooper()).postDelayed(this::startWake,700);
            }catch(Exception e){statusMessage("Não foi possível ativar: "+e.getMessage());}
        });
        action(box,"Desativar Notch",false,()->{
            stopService(new Intent(this,WakeWordService.class));
            stopService(new Intent(this,OverlayService.class));statusMessage("Notch desativado.");
        });
        action(box,"Ajustar posição e tamanho",false,this::showEditor);
        LinearLayout wake=card("Ei, Home","Ativação por voz somente com o Notch ligado. O Android pode usar reconhecimento online. Enquanto ativo, o microfone aparece na notificação.");
        Switch toggle=new Switch(this);
        toggle.setText("Ouvir ‘Ei, Home’");
        toggle.setTextColor(WHITE);toggle.setTextSize(15);
        toggle.setChecked(WakeWordService.enabled(this));
        add(wake,toggle,0,10);
        toggle.setOnCheckedChangeListener((view,on)->{
            getSharedPreferences("home",MODE_PRIVATE).edit().putBoolean("wake_enabled",on).apply();
            if(on)startWake();
            else{stopService(new Intent(this,WakeWordService.class));statusMessage("Ei, Home desligado.");}
        });
        settingSwitch(wake,"Responder em segundo plano com Faber",
            "Após Ei Home, o HOME escuta comandos locais e fala sem abrir a tela. Requer Faber instalada.",
            getSharedPreferences("home",MODE_PRIVATE).getBoolean("wake_background_audio",false),
            (view,on)->{
                if(on && !FaberOffline.isInstalled(this)){
                    view.setChecked(false);
                    statusMessage("Instale a voz Faber em Voz / IA para ativar respostas em segundo plano.");
                    return;
                }
                getSharedPreferences("home",MODE_PRIVATE).edit().putBoolean("wake_background_audio",on).apply();
                statusMessage(on?"Resposta por voz em segundo plano ativada.":"Resposta por voz em segundo plano desativada.");
            });
        action(wake,"Cadastrar minha voz · chamadas e funções",true,this::showVoiceEnrollment);
        action(wake,"Testar o microfone agora",false,()->{openVoiceListening();});
        TextView diag=note("Status: "+getSharedPreferences("home",MODE_PRIVATE).getString("wake_status","Ainda não iniciado."));
        add(wake,diag,6,8);
        action(wake,"Verificar estado da escuta",false,()->{
            android.content.SharedPreferences wakePrefs=getSharedPreferences("home",MODE_PRIVATE);
            long last=wakePrefs.getLong("wake_last_recognized",0);
            String detected=last>0?new java.text.SimpleDateFormat("dd/MM HH:mm:ss",new java.util.Locale("pt","BR")).format(new java.util.Date(last)):"nenhuma ativação reconhecida";
            String sample=wakePrefs.getString("wake_last_hypothesis","nenhuma frase captada");
            String sampleType=wakePrefs.getString("wake_last_hypothesis_type","-");
            long sampleAt=wakePrefs.getLong("wake_last_hypothesis_at",0L);
            String time=sampleAt>0?new java.text.SimpleDateFormat("HH:mm:ss",new java.util.Locale("pt","BR")).format(new java.util.Date(sampleAt)):"-";
            diag.setText("Estado: "+wakePrefs.getString("wake_status","Ainda não iniciado.")
                +"\\nÚltima ativação: "+detected
                +"\\nReconhecimento local ("+sampleType+", "+time+"): "+sample
                +"\\nSe aparecer outra palavra, o microfone está captando, mas o modelo não reconheceu a frase.");
        });
        action(wake,"Reiniciar detector de ativação",false,()->{
            stopService(new Intent(this,WakeWordService.class));
            getSharedPreferences("home",MODE_PRIVATE).edit().putString("wake_status","Reiniciando detector...").apply();
            wakeHandler.postDelayed(this::startWake,750L);
        });
        action(wake,"Testar abertura da escuta",false,()->{
            statusMessage("Teste de conversa: vou abrir o reconhecimento de voz.");
            openVoiceListening();
        });
        add(wake,note("A ativação usa o modelo português offline. Enquanto ligada, a detecção mantém o microfone em uso, sem enviar áudio. O reconhecimento completo só abre após a frase. Ao desativar, a captura é encerrada."),3,0);
    }
    private void updatesPage(){
        LinearLayout box=card("Atualizações oficiais","O aplicativo verifica os lançamentos assinados do HOME.");
        TextView update=note("Versão instalada: "+BuildConfig.VERSION_NAME);
        add(box,update,0,10);
        action(box,"Verificar atualizações",true,()->UpdateHelper.check(this,update));
        action(box,"Abrir downloads oficiais",false,
            ()->startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(DOWNLOAD))));
        action(box,"Mostrar QR Code",false,()->showDownloadQr(box));
    }
    private void exitPage(){
        LinearLayout box=card("Até logo","O HOME pode recolher sem desativar o Notch.");
        action(box,"Recolher HOME",true,this::finish);
        action(box,"Desativar Notch e sair",false,()->requestInlineConfirm(
            "Encerrar HOME","Deseja desligar o Notch e fechar o aplicativo?",()->{
                stopService(new Intent(this,OverlayService.class));finish();
            }));
    }
    private void showEditor(){
        initScreen("editor",null);
        add(root,heading("Editar Notch",narrow()?23:25),0,12);
        add(root,note("Ajuste as medidas com os controles abaixo. As alterações são salvas automaticamente."),0,20);
        android.content.SharedPreferences prefs=getSharedPreferences("home",MODE_PRIVATE);
        LinearLayout options=card("Comportamento da barra","A sobreposição depende das permissões do Android.");
        Switch edge=new Switch(this);
        edge.setText("Integrar à barra superior transparente");
        edge.setTextColor(WHITE);
        edge.setTextSize(14);
        edge.setChecked(prefs.getBoolean("edge_mode",true));
        add(options,edge,0,16);
        edge.setOnCheckedChangeListener((v,on)->{
            prefs.edit().putBoolean("edge_mode",on).apply();refreshNotch();
        });
        Switch handle=new Switch(this);
        handle.setText("Mostrar aba de toque");
        handle.setTextColor(WHITE);
        handle.setTextSize(14);
        handle.setChecked(prefs.getBoolean("touch_tab",true));
        add(options,handle,0,4);
        handle.setOnCheckedChangeListener((v,on)->{
            prefs.edit().putBoolean("touch_tab",on).apply();refreshNotch();
        });
        int width=getResources().getConfiguration().screenWidthDp;
        LinearLayout dimensions=card("Tamanho e posição","Valores em dp; ajuste e veja o resultado no Notch.");
        addPosition(dimensions,"Posição horizontal","offset_x",-180,180,100);
        addPosition(dimensions,"Largura","notch_width",90,Math.max(116,width-8),116);
        addPosition(dimensions,"Altura","notch_height",24,100,34);
        addPosition(dimensions,"Distância entre os olhos","eye_gap",0,Math.max(260,width-50),9);
        addPosition(dimensions,"Posição vertical","offset_y",-60,120,0);
        addPosition(dimensions,"Altura da aba de toque","handle_y",0,48,4);
        LinearLayout restore=card("Restaurar","Retorne aos valores de referência sem apagar outras preferências.");
        action(restore,"Restaurar posição inicial",false,()->requestInlineConfirm(
            "Restaurar medidas","Os controles de posição e tamanho voltarão aos valores iniciais.",()->{
                prefs.edit().putInt("offset_x",100).putInt("offset_y",0)
                    .putInt("notch_width",116).putInt("notch_height",34)
                    .putInt("eye_gap",9).putBoolean("edge_mode",true).apply();
                refreshNotch();showEditor();statusMessage("✓ Medidas restauradas.");
            }));
    }
    private void addPosition(LinearLayout host,String label,String key,int min,int max,int initial){
        android.content.SharedPreferences prefs=getSharedPreferences("home",MODE_PRIVATE);
        TextView caption=text(label+"  ·  "+prefs.getInt(key,initial)+" dp",14);
        add(host,caption,11,7);
        SeekBar slider=new SeekBar(this);
        slider.setMax(max-min);
        slider.setProgress(Math.max(0,Math.min(max-min,prefs.getInt(key,initial)-min)));
        slider.setProgressTintList(android.content.res.ColorStateList.valueOf(BLUE));
        slider.setThumbTintList(android.content.res.ColorStateList.valueOf(BLUE));
        add(host,slider,0,4);
        slider.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
            public void onProgressChanged(SeekBar bar,int progress,boolean user){
                if(!user)return;
                int value=min+progress;
                caption.setText(label+"  ·  "+value+" dp");
                prefs.edit().putInt(key,value).apply();refreshNotch();
            }
            public void onStartTrackingTouch(SeekBar bar){}
            public void onStopTrackingTouch(SeekBar bar){}
        });
    }
    private void refreshNotch(){
        if(Settings.canDrawOverlays(this)){
            try{startService(new Intent(this,OverlayService.class));}
            catch(RuntimeException e){statusMessage("Não foi possível atualizar: "+e.getMessage());}
        }
    }
    @Override public boolean dispatchTouchEvent(android.view.MotionEvent event){
        if(event.getActionMasked()==android.view.MotionEvent.ACTION_DOWN)HomeEmotion.touch();
        return super.dispatchTouchEvent(event);
    }
    @Override protected void onActivityResult(int request,int resultCode,Intent data){
        super.onActivityResult(request,resultCode,data);
        if(request==VOICE_ENROLL_REQUEST){finishEnrollmentCapture(resultCode,data);return;}
        if(request==HomeVoice.REQUEST_SPEECH && (resultCode!=RESULT_OK || data==null)){
            resumeWake();return;
        }
        if(request==HomeVoice.REQUEST_SPEECH && resultCode==RESULT_OK && data!=null){
            pauseWake();
            java.util.ArrayList<String> results=data.getStringArrayListExtra(
                android.speech.RecognizerIntent.EXTRA_RESULTS);
            if(results==null||results.isEmpty()){resumeWake();return;}
            String question=results.get(0);
            if(!"assistant".equals(currentPage))showPage("assistant");
            if(handleLocalCommand(question,true))return;
            statusMessage("Você: "+question+"  ·  HOME está pensando…");
            if(!HomeGroq.connected(this)){
                reportVoiceFailure(question,"A pergunta foi recebida, mas a IA do celular não está conectada. Abra o HOME para configurar a conta.");
                return;
            }
            HomeGroq.ask(this,question,new HomeGroq.Callback(){
                @Override public void onEmotion(String emotion){HomeEmotion.fromGroq(emotion);}
                @Override public void onAnswer(String answer){
                    refreshChat();
                    statusMessage("HOME: "+answer);
                    if(FaberOffline.isInstalled(MainActivity.this))speakAnswer(answer);
                    else {resumeWake();statusMessage("HOME: "+answer+"\nInstale a voz Faber para ouvir.");}
                }
                @Override public void onError(String reason){
                    refreshChat();
                    statusMessage(reason);
                    // HomeGroq já salva a mensagem do usuário; registrar apenas o aviso de erro.
                    try{HomeChatStore.get(MainActivity.this).add("assistant","Não consegui responder: "+reason);}
                    catch(Exception ignored){}
                    refreshChat();
                    if(FaberOffline.isInstalled(MainActivity.this))speakAnswer("Não consegui responder. Veja o aviso na conversa.");
                    else resumeWake();
                }
            });
            refreshChat();
        }
    }
}
