package com.aqnoeu.home;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * Interpretação tolerante da chamada "Ei Home" / "Ok Home", sem dependências do Android
 * (testável com javac puro).
 *
 * O modelo Vosk pt-BR não conhece "home" nem "ok" e costuma transcrever "rome", "homem",
 * "oquei", "o k"... Estas variantes só valem no INÍCIO da frase (aceita apenas um "e" solto
 * antes), para não disparar no meio de conversas comuns. Mesma regra do Windows.
 */
final class WakePhrases {
    private static final Set<String> CALL=new HashSet<>(Arrays.asList(
        "ei","hey","hei","ey","oi","ae","ai","oque","ok","okay","okey","oke","okei","oquei","oquey"));
    /** Como o Vosk pt-BR costuma ouvir "home": o H inicial soa como R ("rôumi"). */
    private static final Set<String> HOME=new HashSet<>(Arrays.asList(
        "home","homi","homy","hom","ome","homem",
        "rome","romi","romy","rhome","rhomi","rom",
        "roume","roumi","roumy","houmi","houme"));
    /** Formas específicas o bastante para valer sozinhas, no início da frase ("Rôumi, que horas são?"). */
    private static final Set<String> BARE=new HashSet<>(Arrays.asList(
        "home","rome","romi","romy","rhome","rhomi","roume","roumi","roumy","houmi","houme"));
    private static final Set<String> JOINED=new HashSet<>();
    static{
        // "okhome", "eiromi", "oqueroumi"... o reconhecedor às vezes cola as duas palavras.
        for(String call:CALL)for(String home:HOME)JOINED.add(call+home);
    }
    private static final Set<String> SPELLED_OK=new HashSet<>(Arrays.asList("k","que","key"));

    private WakePhrases(){}

    /**
     * @param text frase já normalizada (minúsculas, sem acentos, espaços simples)
     * @return o comando que vem depois da chamada ("" se só chamou) ou null se não houve chamada
     */
    static String suffix(String text){
        if(text==null || text.isEmpty())return null;
        String[] words=text.split(" ");
        int limit=words.length>1 && "e".equals(words[0])?2:1;
        for(int i=0;i<limit;i++){
            int next=-1;
            if(JOINED.contains(words[i]))next=i+1;
            else if(i+1<words.length && CALL.contains(words[i]) && HOME.contains(words[i+1]))next=i+2;
            else if(i+2<words.length && "o".equals(words[i]) && SPELLED_OK.contains(words[i+1])
                && HOME.contains(words[i+2]))next=i+3;
            if(next>=0){
                StringBuilder rest=new StringBuilder();
                for(int j=next;j<words.length;j++){
                    if(rest.length()>0)rest.append(' ');
                    rest.append(words[j]);
                }
                return rest.toString();
            }
        }
        return null;
    }

    /**
     * Chamada curta: só o nome ("Home", "Rôumi") no início da frase. Use apenas com resultado
     * final do reconhecedor, para não ativar por palavras soltas durante uma conversa.
     * @return o comando depois do nome, "" se só chamou, ou null
     */
    static String bareSuffix(String text){
        if(text==null || text.isEmpty())return null;
        String[] words=text.split(" ");
        int start=words.length>1 && "e".equals(words[0])?1:0;
        if(BARE.contains(words[start]))return join(words,start+1);
        // "ro me" / "ho me": a palavra partida em duas
        if(start+1<words.length && ("ro".equals(words[start])||"ho".equals(words[start]))
            && ("me".equals(words[start+1])||"mi".equals(words[start+1])))return join(words,start+2);
        return null;
    }
    private static String join(String[] words,int from){
        StringBuilder rest=new StringBuilder();
        for(int j=from;j<words.length;j++){
            if(rest.length()>0)rest.append(' ');
            rest.append(words[j]);
        }
        return rest.toString();
    }
}
