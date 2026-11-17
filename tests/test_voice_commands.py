"""Testes de comandos e ativação sem acessar microfone ou Windows."""
import tempfile
import unittest
from pathlib import Path
from home_voice import interpret, normalize, wake_command, model_is_complete
from home_integrations import load_preferences


class TestVoiceCommands(unittest.TestCase):
    def test_wake_phrase(self):
        self.assertEqual(wake_command("Ei, Home, abrir calculadora"), "abrir calculadora")
        self.assertEqual(wake_command("hey home bloco de notas"), "bloco de notas")
        self.assertIsNone(wake_command("abra calculadora"))
        self.assertIsNone(wake_command("quero dizer ok home"))
        self.assertIsNone(wake_command("eu disse ei home"))
        self.assertEqual(wake_command("ei home"), "")

    def test_wake_variants_from_vosk(self):
        # O Vosk pt-BR transcreve "ok home" de formas variadas.
        for heard in ("ok home", "OK, Home", "okay home", "oquei home", "o k home",
                      "ok rome", "ok homem", "okhome", "e ok home"):
            self.assertEqual(wake_command(heard), "", heard)
        self.assertEqual(wake_command("ok home que horas são"), "que horas sao")
        self.assertEqual(wake_command("ok, home, abra a calculadora"), "abra a calculadora")
        self.assertEqual(wake_command("home"), "")
        self.assertEqual(wake_command("home abrir calculadora"), "abrir calculadora")

    def test_wake_r_sound_variants(self):
        # Em pt-BR o H de "home" soa como R: o Vosk ouve "rôumi", "romi".
        for heard in ("ok roumi", "ei romi", "ai houmi", "eiroumi", "romi", "roumi"):
            self.assertEqual(wake_command(heard), "", heard)
        self.assertEqual(wake_command("roumi que dia é hoje"), "que dia e hoje")

    def test_wake_has_no_false_positive(self):
        for heard in ("roma e linda", "quero ir para rome", "o homem chegou", "ok vamos embora", "minha casa home office",
                      "abra a calculadora", "quero ir para roma", ""):
            self.assertIsNone(wake_command(heard), heard)

    def test_natural_phrases(self):
        self.assertEqual(interpret("por favor, abra a calculadora")[0], "calc")
        self.assertEqual(interpret("pode abrir o bloco de notas")[0], "notepad")
        self.assertEqual(interpret("quero abrir o gerenciador de tarefas")[0], "taskmgr")
        self.assertEqual(interpret("aumentar o volume")[0], "volume_up")
        self.assertEqual(interpret("diminuir o volume")[0], "volume_down")
        self.assertEqual(interpret("abaixar o volume")[0], "volume_down")
        self.assertEqual(interpret("sobe o volume")[0], "volume_up")
        self.assertIsNone(interpret("o que e um volume de esfera"))
        self.assertIsNone(interpret("qual a capital da franca"))

    def test_commands_allowlist(self):
        self.assertEqual(interpret("abra a calculadora")[0], "calc")
        self.assertEqual(interpret("aumente o volume")[0], "volume_up")
        self.assertEqual(interpret("próxima música")[0], "next")
        self.assertIsNone(interpret("apague meus arquivos"))
        self.assertIsNone(interpret("execute powershell"))

    def test_vosk_model_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(model_is_complete(root))
            for file in ("final.mdl", "mfcc.conf", "Gr.fst", "HCLr.fst"):
                (root / file).write_bytes(b"test")
            self.assertTrue(model_is_complete(root))
            (root / "Gr.fst").unlink()
            self.assertFalse(model_is_complete(root))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for file in ("am/final.mdl", "conf/model.conf", "conf/mfcc.conf",
                         "graph/Gr.fst", "graph/HCLr.fst"):
                p = root / file
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"test")
            self.assertTrue(model_is_complete(root))

    def test_normalization(self):
        self.assertEqual(normalize("Próxima MÚSICA"), "proxima musica")

    def test_default_permissions(self):
        defaults = load_preferences()
        for key in ("voice_microphone", "voice_wake", "voice_speech"):
            self.assertIn(key, defaults)


if __name__ == "__main__":
    unittest.main()
