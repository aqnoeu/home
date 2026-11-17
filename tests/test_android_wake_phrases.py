"""Compila WakePhrases.java (sem Android) e testa a chamada "Ok Home" tolerante ao Vosk."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "android/app/src/main/java/com/aqnoeu/home"

HARNESS = """
package com.aqnoeu.home;
public class WakeHarness {
    static int failures=0;
    static void eq(String input,String expected){
        String got=WakePhrases.suffix(input);
        if(expected==null?got!=null:!expected.equals(got)){
            failures++;System.out.println("FALHOU: '"+input+"' -> "+got+" (esperado "+expected+")");
        }
    }
    public static void main(String[] a){
        eq("ok home","");
        eq("ei home","");
        eq("oquei home","");
        eq("o k home","");
        eq("ok rome","");
        eq("ok homem","");
        eq("okhome","");
        eq("e ok home","");
        eq("okey home que horas sao","que horas sao");
        eq("ok home abra a calculadora","abra a calculadora");
        eq("o homem chegou",null);
        eq("ok vamos embora",null);
        eq("quero ir para roma",null);
        eq("abra a calculadora",null);
        eq("",null);
        eq(null,null);
        System.out.println(failures==0?"OK":"FALHAS="+failures);
        System.exit(failures==0?0:1);
    }
}
"""


class AndroidWakePhrasesTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("javac") and shutil.which("java"), "JDK indisponível")
    def test_wake_phrase_variants_compile_and_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            harness = out / "WakeHarness.java"
            harness.write_text(HARNESS, encoding="utf-8")
            build = subprocess.run(
                ["javac", "-d", str(out), str(SRC / "WakePhrases.java"), str(harness)],
                capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run(["java", "-cp", str(out), "com.aqnoeu.home.WakeHarness"],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_service_uses_tolerant_parser_and_opens_chat_from_background(self):
        wake = (SRC / "WakeWordService.java").read_text(encoding="utf-8")
        main = (SRC / "MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("return WakePhrases.suffix(text);", wake)
        self.assertIn("canOpenChatFromBackground()", wake)
        self.assertIn("Settings.canDrawOverlays(this)", wake)
        self.assertIn("startActivity(open);", wake)
        self.assertIn("postWakeNotification(open);", wake)
        # "\\n" literal aparecia na notificação de resposta
        self.assertNotIn('"\\\\nHOME: "', wake)
        self.assertIn('.cancel(73)', main)
        self.assertIn("reportVoiceFailure(question,", main)

    def test_groq_network_errors_are_explained(self):
        groq = (SRC / "HomeGroq.java").read_text(encoding="utf-8")
        self.assertIn("SocketTimeoutException", groq)
        self.assertIn("Verifique a internet do celular", groq)
        self.assertIn('"max_completion_tokens",900', groq)


if __name__ == "__main__":
    unittest.main()
