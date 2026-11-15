"""Testes de comandos e ativação sem acessar microfone ou Windows."""
import unittest
from home_voice import interpret, normalize, wake_command
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

    def test_normalization(self):
        self.assertEqual(normalize("Próxima MÚSICA"), "proxima musica")

    def test_default_permissions(self):
        defaults = load_preferences()
        for key in ("voice_microphone", "voice_wake", "voice_speech"):
            self.assertIn(key, defaults)


if __name__ == "__main__":
    unittest.main()
