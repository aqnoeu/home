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
        self.assertEqual(wake_command("ei home"), "")

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
