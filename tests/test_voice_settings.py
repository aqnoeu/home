"""Seleção de vozes instaladas, velocidade e volume da fala do Home."""
import unittest
from types import SimpleNamespace
from home_voice import preferred_voice, SpeechWorker


class VoiceSettingsTests(unittest.TestCase):
    def setUp(self):
        self.voices = [
            SimpleNamespace(id="english-voice", name="English", languages=["en-US"]),
            SimpleNamespace(id="brazil-voice", name="Português Brasil", languages=["pt-BR"]),
        ]

    def test_prefers_portuguese_when_not_selected(self):
        self.assertEqual(preferred_voice(self.voices), "brazil-voice")

    def test_respects_selected_voice(self):
        self.assertEqual(preferred_voice(self.voices, "english-voice"), "english-voice")

    def test_nonexistent_voice_falls_back(self):
        self.assertEqual(preferred_voice(self.voices, "missing"), "brazil-voice")

    def test_no_voice_available(self):
        self.assertIsNone(preferred_voice([], "old-id"))

    def test_rate_and_volume_are_clamped(self):
        worker = SpeechWorker("Teste", "", 999, -10)
        self.assertEqual(worker.rate, 280)
        self.assertEqual(worker.volume, 0)


if __name__ == "__main__":
    unittest.main()
