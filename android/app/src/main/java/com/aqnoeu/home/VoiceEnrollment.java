package com.aqnoeu.home;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.text.Normalizer;
import java.util.Locale;

/** Local, user-reviewed wake phrase onboarding. This does not train a speaker biometric model. */
public final class VoiceEnrollment {
    private static final String PREF="home_voice_enrollment";
    private static final String[] PROMPTS={
        "Ei Home","Ok Home","Home",
        "Ei Home, que horas são?",
        "Ok Home, que dia é hoje?",
        "Home, qual a bateria do celular?"
    };
    private VoiceEnrollment(){}
    public static int count(){return PROMPTS.length;}
    public static String prompt(int step){return PROMPTS[Math.max(0,Math.min(step,PROMPTS.length-1))];}
    public static int step(Context ctx){return Math.min(count(),Math.max(0,p(ctx).getInt("step",0)));}
    public static boolean corrections(Context ctx){return p(ctx).getBoolean("corrections",true);}
    public static void setCorrections(Context ctx,boolean enabled){p(ctx).edit().putBoolean("corrections",enabled).apply();}
    private static SharedPreferences p(Context ctx){return ctx.getSharedPreferences(PREF,Context.MODE_PRIVATE);}
    public static String normalize(String input){
        if(input==null)return "";
        return Normalizer.normalize(input.toLowerCase(new Locale("pt","BR")),Normalizer.Form.NFD)
            .replaceAll("\\p{M}+","").replaceAll("[^a-z0-9 ]+"," ")
            .replaceAll("\\s+"," ").trim();
    }
    private static boolean expected(int step,String heard){
        String q=normalize(heard);
        String wake=step%3==0?"ei home":step%3==1?"ok home":"home";
        if(step<3)return q.equals(wake)||("ei home".equals(wake)&&q.equals("hey home"));
        // Require both activation and function, not merely wake words.
        boolean hasWake=q.startsWith(wake+" ")||("ei home".equals(wake)&&q.startsWith("hey home "));
        if(!hasWake)return false;
        if(step==3)return q.contains("hora");
        if(step==4)return q.contains("dia")&&q.contains("hoje");
        return q.contains("bateria")||q.contains("carga");
    }
    public static boolean matches(int step,String heard){return expected(step,heard);}
    /** Stores only text. Real training audio and speaker identity are not inferred. */
    public static void accept(Context ctx,String heard,boolean corrected){
        int s=step(ctx);
        if(s>=count())return;
        try{
            JSONArray samples=new JSONArray(p(ctx).getString("samples","[]"));
            JSONObject item=new JSONObject();
            item.put("step",s);item.put("expected",prompt(s));item.put("heard",heard);
            item.put("corrected",corrected);item.put("time",System.currentTimeMillis());
            samples.put(item);
            SharedPreferences.Editor edit=p(ctx).edit().putString("samples",samples.toString()).putInt("step",s+1);
            // Only store corrected text aliases for opt-in use. Never infer identity.
            if(corrected&&corrections(ctx)){
                String candidate=normalize(heard);
                if(s<3 && candidate.length()>=5 && candidate.length()<=28
                    && candidate.split(" ").length<=3 && !candidate.equals("home")){
                    JSONArray aliases=new JSONArray(p(ctx).getString("aliases","[]"));
                    boolean exists=false;
                    for(int i=0;i<aliases.length();i++)if(candidate.equals(aliases.optString(i)))exists=true;
                    if(!exists && aliases.length()<15)aliases.put(candidate);
                    edit.putString("aliases",aliases.toString());
                }
            }
            edit.apply();
        }catch(Exception ignored){}
    }
    /** Accepts only explicitly confirmed full-phrase aliases, always as a prefix. */
    public static String aliasSuffix(Context ctx,String phrase,boolean isFinal){
        if(!corrections(ctx)||!isFinal)return null;
        String text=normalize(phrase);
        try{
            JSONArray aliases=new JSONArray(p(ctx).getString("aliases","[]"));
            for(int i=0;i<aliases.length();i++){
                String prefix=aliases.optString(i);
                if(prefix.length()<5)continue;
                if(text.equals(prefix))return "";
                if(text.startsWith(prefix+" "))return text.substring(prefix.length()).trim();
            }
        }catch(Exception ignored){}
        return null;
    }
    public static String summary(Context ctx){
        int done=step(ctx);
        return done==count()?"Cadastro concluído: "+done+" de "+count()+" testes."
            :"Teste "+(done+1)+" de "+count()+" — "+(done<3?"chamada isolada":"chamada + função");
    }
    public static void reset(Context ctx){p(ctx).edit().clear().apply();}
}
