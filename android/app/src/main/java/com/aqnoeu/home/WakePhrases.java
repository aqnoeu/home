package com.aqnoeu.home;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * Interpretação tolerante da chamada "Ei Home" / "Ok Home", sem dependências do Android
 * (testável com javac puro).
 *
 * O modelo Vosk pt-BR não conhece "home" nem "ok" e costuma transcrever "rome", "homem",
 * "oquei", "o k"... Estas variantes só valem no INÍCIO da frase (até duas palavras de ruído
 * antes), para não disparar com conversas comuns.
 */
final class WakePhrases {
    private static final Set<String> CALL=new HashSet<>(Arrays.asList(
        "ei","hey","hei","ey","oi","ok","okay","okey","oke","okei","oquei","oquey"));
    private static final Set<String> HOME=new HashSet<>(Arrays.asList(
        "home","rome","romi","homi","hom","ome","rhome","rom","homem","roume"));
    private static final Set<String> JOINED=new HashSet<>(Arrays.asList(
        "okhome","eihome","heyhome","okayhome","okrome","eirome","oquehome"));
    private static final Set<String> SPELLED_OK=new HashSet<>(Arrays.asList("k","que","key"));

    private WakePhrases(){}

    /**
     * @param text frase já normalizada (minúsculas, sem acentos, espaços simples)
     * @return o comando que vem depois da chamada ("" se só chamou) ou null se não houve chamada
     */
    static String suffix(String text){
        if(text==null || text.isEmpty())return null;
        String[] words=text.split(" ");
        int limit=Math.min(3,words.length);
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
}
