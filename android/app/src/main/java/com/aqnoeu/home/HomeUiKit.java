package com.aqnoeu.home;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.text.InputType;
import android.view.Gravity;
import android.widget.*;

/**
 * Small, stateless Android UI factory except for the current screen container.
 * MainActivity owns navigation/lifecycle; this class owns only reusable views.
 * The original size, colors, labels and callbacks are intentionally preserved.
 */
public final class HomeUiKit {
    private static final int BG=Color.rgb(11,17,26);
    private static final int SURFACE=Color.rgb(20,29,42);
    private static final int RAISED=Color.rgb(29,40,56);
    private static final int LINE=Color.rgb(49,62,80);
    private static final int WHITE=Color.WHITE;
    private static final int MUTED=Color.rgb(176,188,204);
    private static final int BLUE=Color.rgb(47,107,255);
    private final Activity activity;
    private LinearLayout root;
    public HomeUiKit(Activity activity){this.activity=activity;}
    public void setRoot(LinearLayout root){this.root=root;}
    public int dp(float n) {return Math.round(n*activity.getResources().getDisplayMetrics().density);}
    public boolean narrow(){return activity.getResources().getConfiguration().screenWidthDp<440;}
    public GradientDrawable bg(int color,int radius){
        GradientDrawable d=new GradientDrawable();
        d.setColor(color);d.setCornerRadius(dp(radius));
        if(color!=BLUE)d.setStroke(dp(1),LINE);
        return d;
    }
    public TextView text(String value,int sp,int color,boolean heavy){
        TextView t=new TextView(activity);
        t.setText(value);t.setTextSize(sp);t.setTextColor(color);t.setIncludeFontPadding(false);
        t.setTypeface(android.graphics.Typeface.create("sans-serif",
            heavy?android.graphics.Typeface.BOLD:android.graphics.Typeface.NORMAL));
        t.setLineSpacing(dp(2),1.02f);
        t.setBreakStrategy(android.text.Layout.BREAK_STRATEGY_HIGH_QUALITY);
        t.setHyphenationFrequency(android.text.Layout.HYPHENATION_FREQUENCY_NONE);
        return t;
    }
    public TextView text(String value,int sp){return text(value,sp,WHITE,false);}
    public TextView heading(String value,int sp){return text(value,sp,WHITE,true);}
    public TextView note(String value){return text(value,13,MUTED,false);}
    public LinearLayout.LayoutParams space(int top,int bottom){
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);
        p.topMargin=dp(top);p.bottomMargin=dp(bottom);return p;
    }
    public void add(LinearLayout host,View view,int top,int bottom){host.addView(view,space(top,bottom));}
    public LinearLayout column(){
        LinearLayout l=new LinearLayout(activity);l.setOrientation(LinearLayout.VERTICAL);return l;
    }
    public LinearLayout card(String title,String description){
        LinearLayout l=column();
        l.setBackground(bg(SURFACE,16));
        l.setPadding(dp(16),dp(16),dp(16),dp(16));
        if(title!=null&&!title.isEmpty())add(l,heading(title,17),0,description==null?12:7);
        if(description!=null&&!description.isEmpty())add(l,note(description),0,12);
        add(root,l,0,12);
        return l;
    }
    public Button button(String value,boolean primary,Runnable click){
        Button b=new Button(activity);
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
    public void action(LinearLayout target,String label,boolean primary,Runnable run){
        add(target,button(label,primary,run),4,8);
    }
    public void actions(LinearLayout target,String left,Runnable a,String right,Runnable b){
        LinearLayout row=new LinearLayout(activity);
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
    public EditText edit(String hint,boolean secret){
        EditText e=new EditText(activity);
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
}
