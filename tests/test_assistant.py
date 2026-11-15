"""Testes para interpretação segura de mensagens digitadas."""
import unittest
from datetime import datetime

from home_assistant import typed_response


class AssistantResponseTests(unittest.TestCase):
    def test_greeting_without_ai(self):
        reply, action = typed_response("Olá!")
        self.assertIn("Olá!", reply)
        self.assertIsNone(action)

    def test_voice_without_microphone(self):
        reply, action = typed_response("teste de voz")
        self.assertIn("Não preciso do microfone", reply)
        self.assertIsNone(action)

    def test_time_uses_local_clock(self):
        reply, action = typed_response("Que horas são?", datetime(2026, 11, 15, 18, 3))
        self.assertEqual(reply, "Agora são 18:03.")
        self.assertIsNone(action)

    def test_windows_action_requires_confirmation_in_ui(self):
        reply, action = typed_response("Abra a calculadora")
        self.assertEqual(action, "calc")
        self.assertIn("Calculadora", reply)

    def test_unknown_commands_do_not_execute(self):
        for value in ("apague meus arquivos", "execute powershell", "formate o disco"):
            _, action = typed_response(value)
            self.assertIsNone(action)

    def test_empty_does_not_execute(self):
        reply, action = typed_response(" ")
        self.assertIsNone(action)
        self.assertIn("Digite", reply)


if __name__ == "__main__":
    unittest.main()
