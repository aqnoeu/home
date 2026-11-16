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
    private String currentPage = "hub";
    private static final int WAKE_PERMISSION_REQUEST = 721;
    private boolean wakeBusy = false;

    private int dp(float n) {return Math.round(n*getResources().getDisplayMetrics().density);}
    private boolean narrow(){return getResources().getConfiguration().screenWidthDp<440;}
    private GradientDrawable bg(int color,int radius){
        GradientDrawable d=new GradientDrawable();
        d.setColor(color);d.setCornerRadius(dp(radius));
        if(color!=BLUE)d.setStroke(dp(1),LINE);
        return d;
    }
    private TextView text(String value,int sp,int color,boolean heavy){
        TextView t=new TextView(this);
        t.setText(value);t.setTextSize(sp);t.setTextColor(color);t.setIncludeFontPadding(false);
        t.setTypeface(android.graphics.Typeface.create("sans-serif",
            heavy?android.graphics.Typeface.BOLD:android.graphics.Typeface.NORMAL));
        t.setLineSpacing(dp(4),1.04f);
        t.setBreakStrategy(android.text.Layout.BREAK_STRATEGY_HIGH_QUALITY);
        t.setHyphenationFrequency(android.text.Layout.HYPHENATION_FREQUENCY_NONE);
        return t;
    }
    private TextView text(String value,int sp){return text(value,sp,WHITE,false);}
    private TextView heading(String value,int sp){return text(value,sp,WHITE,true);}
    private TextView note(String value){return text(value,13,MUTED,false);}
    private LinearLayout.LayoutParams space(int top,int bottom){
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);
        p.topMargin=dp(top);p.bottomMargin=dp(bottom);return p;
    }
    private void add(LinearLayout host,View view,int top,int bottom){host.addView(view,space(top,bottom));}
    private LinearLayout column(){
        LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);return l;
    }
    private LinearLayout card(String title,String description){
        LinearLayout l=column();
        l.setBackground(bg(SURFACE,16));
        l.setPadding(dp(16),dp(16),dp(16),dp(16));
        if(title!=null&&!title.isEmpty())add(l,heading(title,17),0,description==null?12:7);
        if(description!=null&&!description.isEmpty())add(l,note(description),0,12);
        add(root,l,0,12);
        return l;
    }
    private Button button(String value,boolean primary,Runnable click){
        Button b=new Button(this);
        b.setText(value);b.setAllCaps(false);b.setTextSize(14);
        b.setTypeface(android.graphics.Typeface.create("sans-serif-medium",0));
        b.setMinHeight(dp(48));b.setMinimumHeight(dp(48));
        b.setGravity(Gravity.CENTER);
        b.setSingleLine(false);
        b.setMaxLines(2);
        b.setBreakStrategy(android.text.Layout.BREAK_STRATEGY_HIGH_QUALITY);
        b.setTextColor(WHITE);
        b.setBackground(bg(primary?BLUE:RAISED,13));
        b.setPadding(dp(10),dp(8),dp(10),dp(8));
        b.setOnClickListener(v->click.run());
        return b;
    }
    private void action(LinearLayout target,String label,boolean primary,Runnable run){
        add(target,button(label,primary,run),4,8);
    }
    private void actions(LinearLayout target,String left,Runnable a,String right,Runnable b){
        LinearLayout row=new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        Button first=button(left,true,a),second=button(right,false,b);
        first.setTextSize(narrow()?12:14);
        second.setTextSize(narrow()?12:14);
        LinearLayout.LayoutParams one=new LinearLayout.LayoutParams(0,dp(54),1);
        one.rightMargin=dp(5);row.addView(first,one);
        LinearLayout.LayoutParams two=new LinearLayout.LayoutParams(0,dp(54),1);
        two.leftMargin=dp(5);row.addView(second,two);
        add(target,row,2,8);
    }
    private EditText edit(String hint,boolean secret){
        EditText e=new EditText(this);
        e.setTextColor(WHITE);e.setHintTextColor(MUTED);e.setHint(hint);
        e.setTextSize(15);e.setSingleLine(secret);
        e.setInputType(secret?InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD:
            InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_CAP_SENTENCES|InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        e.setBackground(bg(RAISED,13));
        e.setPadding(dp(15),dp(12),dp(15),dp(12));
        e.setMinimumHeight(dp(52));
        if(!secret){e.setMinLines(2);e.setMaxLines(4);}
        return e;
    }
    private void showStatus(String value){if(status!=null)status.setText(value);}
    public void reportVoiceStatus(String message){statusMessage(message);}
    private void success(TextView view,String message){view.setText("✓ "+message);view.setTextColor(GREEN);}
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);
        VoiceCleanup.cleanup(this);
        showHub();
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
        wakeBusy=true;
        pauseWake();
        showPage("assistant");
        if(query.trim().isEmpty()){
            statusMessage("Estou ouvindo. Pode falar.");
            HomeVoice.listen(this);
        }else{
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
        try{
            startForegroundService(new Intent(this,WakeWordService.class));
            statusMessage("Ei, Home habilitado. Verifique a notificação do microfone.");
        }catch(Exception e){statusMessage("Falha ao iniciar escuta: "+e.getMessage());}
    }
    private void pauseWake(){
        if(WakeWordService.enabled(this)){
            wakeBusy=true;
            wakeHandler.removeCallbacksAndMessages(null);
            try{startService(new Intent(this,WakeWordService.class).setAction(WakeWordService.PAUSE));}
            catch(Exception ignored){}
        }
    }
    private void speakAnswer(String answer){
        if(FaberOffline.isInstalled(this)){
            FaberOffline.speak(this,answer,message->{
                if(message.startsWith("✓ Faber reproduzida") || message.startsWith("Falha") || message.startsWith("Instale"))resumeWake();
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
        },12000);
    }
    @Override public void onRequestPermissionsResult(int request,String[] perms,int[] results){
        super.onRequestPermissionsResult(request,perms,results);
        if(request==WAKE_PERMISSION_REQUEST){
            if(results.length>0 && results[0]==PackageManager.PERMISSION_GRANTED)startWake();
            else statusMessage("Permissão de microfone negada. Ei, Home não está ouvindo.");
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
        ImageView icon=new ImageView(this);
        icon.setImageResource(R.drawable.home_logo_transparent);
        icon.setScaleType(ImageView.ScaleType.FIT_CENTER);
        icon.setContentDescription("Símbolo oficial HOME: dois olhos brancos em fundo grafite");
        LinearLayout.LayoutParams iconSize=new LinearLayout.LayoutParams(dp(48),dp(48));
        iconSize.rightMargin=dp(10);
        brand.addView(icon,iconSize);
        LinearLayout brandCopy=column();
        add(brandCopy,heading("HOME",21),0,4);
        add(brandCopy,note("Um assistente para você."),0,0);
        brand.addView(brandCopy,new LinearLayout.LayoutParams(0,-2,1));
        add(root,brand,0,16);
        View line=new View(this);line.setBackgroundColor(LINE);
        root.addView(line,new LinearLayout.LayoutParams(-1,dp(1)));
        if(!"hub".equals(page)){
            Button back=button("‹  Voltar",false,this::showHub);
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
        eyes.setMood(prefs.getInt("mood",0));eyes.setEyeGap(prefs.getInt("eye_gap",9));
        eyes.setBackground(bg(BG,18));
        LinearLayout.LayoutParams eyesSize=new LinearLayout.LayoutParams(-1,dp(86));
        eyesSize.bottomMargin=dp(8);
        face.addView(eyes,eyesSize);
        add(face,note("Expressão"),0,9);
        HorizontalScrollView hscroll=new HorizontalScrollView(this);
        hscroll.setHorizontalScrollBarEnabled(false);
        LinearLayout moods=new LinearLayout(this);moods.setOrientation(LinearLayout.HORIZONTAL);
        String[] labels={"Normal","Feliz","Sonolento","Bravo"};
        for(int i=0;i<labels.length;i++){
            final int index=i;
            Button mood=button(labels[i],false,()->{
                prefs.edit().putInt("mood",index).apply();
                eyes.setMood(index);
                if(Settings.canDrawOverlays(this))refreshNotch();
                showStatus("Expressão: "+labels[index]);
                status.setVisibility(View.VISIBLE);
            });
            LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(dp(94),dp(46));
            p.rightMargin=dp(8);moods.addView(mood,p);
        }
        hscroll.addView(moods);
        face.addView(hscroll);

        add(root,heading("Acesso rápido",18),9,12);
        LinearLayout quick=column();
        actions(quick,"Conversar",()->showPage("assistant"),
            "Microfone",()->showPage("voice"));
        actions(quick,"Notch e Ei, Home",()->showPage("interactions"),"Ajustar aparência",this::showEditor);
        actions(quick,"Atualizações",()->showPage("updates"),"Sair",()->showPage("exit"));
        add(root,quick,0,12);

        add(root,note("HOME · v"+BuildConfig.VERSION_NAME+" · @aqnoeu"),17,0);
    }
    private void showPage(String page){
        String title=page.equals("assistant")?"Assistente":
            page.equals("voice")?"Voz e microfone":
            page.equals("interactions")?"Interações":
            page.equals("updates")?"Atualizações":"Encerrar";
        initScreen(page,null);
        add(root,heading(title,narrow()?22:24),0,12);
        switch(page){
            case "assistant": assistantPage();break;
            case "voice": voicePage();break;
            case "interactions": interactionPage();break;
            case "updates": updatesPage();break;
            default: exitPage();
        }
    }
    /** A real chat layout: independent message scroll and a fixed input dock. */
    private void assistantPage(){
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        LinearLayout shell=column();
        shell.setBackgroundColor(BG);
        shell.setFocusableInTouchMode(true);
        final int horizontal=dp(14);
        shell.setPadding(horizontal,dp(12),horizontal,dp(12));
        shell.setOnApplyWindowInsetsListener((view,insets)->{
            if(Build.VERSION.SDK_INT>=30){
                android.graphics.Insets bars=insets.getInsets(
                    WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());
                android.graphics.Insets keyboard=insets.getInsets(WindowInsets.Type.ime());
                shell.setPadding(horizontal,bars.top+dp(10),horizontal,
                    Math.max(bars.bottom,keyboard.bottom)+dp(8));
            }
            return insets;
        });
        setContentView(shell);
        shell.requestApplyInsets();

        LinearLayout top=new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        Button back=button("‹",false,this::showHub);
        back.setTextSize(22);
        top.addView(back,new LinearLayout.LayoutParams(dp(48),dp(48)));
        LinearLayout titleBox=column();
        TextView label=heading("HOME",19);
        add(titleBox,label,0,3);
        TextView state=note(HomeGroq.connected(this)?"● Groq conectada":"● Groq desconectada");
        state.setTextColor(HomeGroq.connected(this)?GREEN:MUTED);
        add(titleBox,state,0,0);
        LinearLayout.LayoutParams titleParams=new LinearLayout.LayoutParams(0,-2,1);
        titleParams.leftMargin=dp(12);
        top.addView(titleBox,titleParams);
        Button newChat=button("+",false,()->{
            HomeChatStore.get(this).newChat();
            refreshChat();
            if(chatPicker!=null && chatPicker.getParent()!=null)
                ((View)chatPicker.getParent()).setVisibility(View.GONE);
        });
        newChat.setContentDescription("Nova conversa");
        newChat.setTextSize(23);
        top.addView(newChat,new LinearLayout.LayoutParams(dp(48),dp(48)));
        shell.addView(top,new LinearLayout.LayoutParams(-1,-2));

        LinearLayout infoRow=new LinearLayout(this);
        infoRow.setOrientation(LinearLayout.HORIZONTAL);
        infoRow.setGravity(Gravity.CENTER_VERTICAL);
        chatTitle=note("Conversa atual");
        chatTitle.setSingleLine(true);
        chatTitle.setEllipsize(android.text.TextUtils.TruncateAt.END);
        infoRow.addView(chatTitle,new LinearLayout.LayoutParams(0,dp(44),1));
        chatTitle.setGravity(Gravity.CENTER_VERTICAL);
        Button history=button("Conversas ▾",false,()->{
            if(chatPicker.getVisibility()==View.VISIBLE) chatPicker.setVisibility(View.GONE);
            else { renderChatList(); chatPicker.setVisibility(View.VISIBLE); }
        });
        history.setTextSize(12);
        infoRow.addView(history,new LinearLayout.LayoutParams(dp(126),dp(44)));
        shell.addView(infoRow,new LinearLayout.LayoutParams(-1,-2));

        ScrollView pickerScroll=new ScrollView(this);
        pickerScroll.setFillViewport(false);
        pickerScroll.setBackground(bg(SURFACE,14));
        pickerScroll.setVerticalScrollBarEnabled(true);
        chatPicker=column();
        chatPicker.setPadding(dp(8),dp(8),dp(8),dp(8));
        pickerScroll.addView(chatPicker,new ScrollView.LayoutParams(-1,-2));
        pickerScroll.setVisibility(View.GONE);
        // Keep the list from growing beyond the available screen.
        shell.addView(pickerScroll,new LinearLayout.LayoutParams(-1,dp(190)));
        pickerScroll.setVisibility(View.GONE);
        // The button is connected to the bounded ScrollView instead of the unbounded list.
        history.setOnClickListener(v->{
            if(pickerScroll.getVisibility()==View.VISIBLE)pickerScroll.setVisibility(View.GONE);
            else{renderChatList();pickerScroll.setVisibility(View.VISIBLE);}
        });

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
        chatMessages.setPadding(dp(2),dp(10),dp(2),dp(12));
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
        dock.setBackground(bg(RAISED,22));
        dock.setPadding(dp(6),dp(5),dp(6),dp(5));

        Button mic=button("◉",false,()->{
            pauseWake();HomeVoice.listen(this);
        });
        mic.setTextSize(20);
        mic.setContentDescription("Falar com o Home");
        mic.setBackgroundColor(Color.TRANSPARENT);
        dock.addView(mic,new LinearLayout.LayoutParams(dp(44),dp(48)));

        chatInput=new EditText(this);
        chatInput.setHint("Mensagem para o HOME…");
        chatInput.setHintTextColor(MUTED);
        chatInput.setTextColor(WHITE);
        chatInput.setTextSize(15);
        chatInput.setIncludeFontPadding(false);
        chatInput.setSingleLine(false);
        chatInput.setMinLines(1);chatInput.setMaxLines(5);
        chatInput.setGravity(Gravity.CENTER_VERTICAL|Gravity.START);
        chatInput.setInputType(InputType.TYPE_CLASS_TEXT|
            InputType.TYPE_TEXT_FLAG_CAP_SENTENCES|InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        chatInput.setPadding(dp(6),dp(9),dp(6),dp(9));
        chatInput.setBackgroundColor(Color.TRANSPARENT);
        chatInput.setFilters(new android.text.InputFilter[]{
            new android.text.InputFilter.LengthFilter(750)});
        dock.addView(chatInput,new LinearLayout.LayoutParams(0,-2,1f));

        Button send=button("➤",true,()->sendChatMessage());
        send.setTextSize(20);
        send.setContentDescription("Enviar mensagem");
        LinearLayout.LayoutParams sendParams=new LinearLayout.LayoutParams(dp(46),dp(46));
        sendParams.leftMargin=dp(3);
        dock.addView(send,sendParams);
        LinearLayout.LayoutParams dockParams=new LinearLayout.LayoutParams(-1,-2);
        dockParams.topMargin=dp(6);
        shell.addView(dock,dockParams);

        inlineHost=column();
        shell.addView(inlineHost,new LinearLayout.LayoutParams(-1,-2));
        refreshChat();
        shell.requestFocus();

        // Connection management is hidden behind a long press on the connection indicator.
        state.setOnClickListener(v->showConnectionSettings(state));
        state.setText(state.getText()+" · toque para configurar");
    }

    private void showConnectionSettings(TextView state){
        clearInline();
        LinearLayout panel=column();
        panel.setPadding(dp(12),dp(12),dp(12),dp(12));
        panel.setBackground(bg(SURFACE,14));
        add(panel,heading("Conexão Groq",16),0,6);
        EditText secret=edit("Chave Groq · gsk_…",true);
        add(panel,secret,0,7);
        action(panel,"Salvar chave",true,()->{
            try{
                HomeGroq.connect(this,secret.getText().toString());
                secret.setText("");
                state.setText("● Groq conectada · toque para configurar");
                state.setTextColor(GREEN);
                clearInline();
                statusMessage("Conexão Groq salva.");
            }catch(Exception e){statusMessage("Não foi possível conectar: "+e.getMessage());}
        });
        action(panel,"Desconectar",false,()->requestInlineConfirm(
            "Desconectar Groq","Suas conversas salvas serão preservadas.",()->{
                HomeGroq.disconnect(this);
                state.setText("● Groq desconectada · toque para configurar");
                state.setTextColor(MUTED);
            }));
        action(panel,"Fechar",false,this::clearInline);
        inlineHost.addView(panel,new LinearLayout.LayoutParams(-1,-2));
    }

    private void sendChatMessage(){
        if(chatInput==null)return;
        String q=chatInput.getText().toString().trim();
        if(q.isEmpty())return;
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
        TextView body=text(message,15,WHITE,false);
        body.setMaxWidth(Math.round(getResources().getDisplayMetrics().widthPixels*0.80f));
        body.setBackground(bg(user?BLUE:RAISED,16));
        body.setPadding(dp(15),dp(12),dp(15),dp(12));
        LinearLayout.LayoutParams bodySize=new LinearLayout.LayoutParams(-2,-2);
        bodySize.leftMargin=user?dp(27):0;
        bodySize.rightMargin=user?0:dp(27);
        line.addView(body,bodySize);
        add(chatMessages,line,0,12);
    }
    private void refreshChat(){
        if(chatMessages==null||!"assistant".equals(currentPage))return;
        HomeChatStore store=HomeChatStore.get(this);
        String id=store.ensureActive();
        String title="Nova conversa";
        for(JSONObject c:store.conversations()){
            if(id.equals(c.optString("id"))){title=c.optString("title","Conversa");break;}
        }
        if(chatTitle!=null)chatTitle.setText("Atual: "+title);
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
                ((View)chatPicker.getParent()).setVisibility(View.GONE);
                refreshChat();
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
            if(response!=null)response.setText("Conecte a Groq na seção Assistente para fazer perguntas.");
            else statusMessage("Conecte a Groq na seção Assistente.");
            resumeWake();
            return;
        }
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
        action(microphone,"◉ Perguntar por voz",true,()->{pauseWake();HomeVoice.listen(this);});
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
        action(wake,"Testar o microfone agora",false,()->{pauseWake();HomeVoice.listen(this);});
        TextView diag=note("Status: "+getSharedPreferences("home",MODE_PRIVATE).getString("wake_status","Ainda não iniciado."));
        add(wake,diag,6,8);
        action(wake,"Verificar estado da escuta",false,()->diag.setText("Status: "+getSharedPreferences("home",MODE_PRIVATE).getString("wake_status","Ainda não iniciado.")));
        add(wake,note("O Android pode interromper o reconhecimento contínuo. Se o sistema bloquear, o teste manual permanece disponível."),3,0);
    }
    private void updatesPage(){
        LinearLayout box=card("Atualizações oficiais","O aplicativo verifica os lançamentos assinados do HOME.");
        TextView update=note("Versão instalada: "+BuildConfig.VERSION_NAME);
        add(box,update,0,10);
        action(box,"Verificar atualizações",true,()->UpdateHelper.check(this,update));
        action(box,"Abrir downloads oficiais",false,
            ()->startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(DOWNLOAD))));
        action(box,"Mostrar QR Code",false,()->{
            // QR is rendered inline; no dialog covers the screen.
            try{
                BitMatrix matrix=new MultiFormatWriter().encode(DOWNLOAD,BarcodeFormat.QR_CODE,260,260);
                Bitmap bitmap=Bitmap.createBitmap(260,260,Bitmap.Config.ARGB_8888);
                for(int y=0;y<260;y++)for(int x=0;x<260;x++)
                    bitmap.setPixel(x,y,matrix.get(x,y)?Color.BLACK:WHITE);
                ImageView image=new ImageView(this);
                image.setContentDescription("QR Code para a página oficial de downloads");
                image.setImageBitmap(bitmap);
                image.setBackground(bg(WHITE,14));
                image.setPadding(dp(12),dp(12),dp(12),dp(12));
                LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,dp(270));
                p.topMargin=dp(14);box.addView(image,p);
            }catch(Exception e){update.setText("Não foi possível criar o QR Code: "+e.getMessage());}
        });
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
            statusMessage("Você: "+question+"  ·  HOME está pensando…");
            if(!HomeGroq.connected(this)){
                statusMessage("Conecte a Groq no Assistente para receber respostas por voz.");
                resumeWake();return;
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
                    resumeWake();
                    refreshChat();
                    statusMessage(reason);
                }
            });
            refreshChat();
        }
    }
}
