"""Regressão: olhos não devem pulsar após resposta falada."""
import os
import unittest
from unittest.mock import MagicMock, patch
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget
from home import EyesWidget
from home_voice import VoiceManager


class EyeSpeechTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.eyes = EyesWidget()
        self.eyes.timer.stop()
        self.home = QWidget()
        self.home.eyes = self.eyes
        self.home.integration_prefs = {"voice_wake": False, "voice_microphone": False}
        self.manager = VoiceManager(self.home)

    def tearDown(self):
        self.eyes.close()
        self.home.close()

    def test_speech_completion_always_clears_visual_state(self):
        speaker = MagicMock()
        self.manager.speaker = speaker
        self.manager.set_state("speaking")
        self.assertEqual(self.eyes.voice_state, "speaking")
        self.manager.speech_finished(speaker)
        self.assertEqual(self.eyes.voice_state, "")

    def test_pending_action_does_not_leave_thinking_state(self):
        self.home.integration_prefs["windows_controls"] = True
        self.manager.set_state("thinking")
        self.manager.handle_heard("abra a calculadora")
        self.assertEqual(self.eyes.voice_state, "")
        self.assertIsNotNone(self.manager.pending_action)

    def test_voice_state_clears_even_when_wake_requested(self):
        speaker = MagicMock()
        self.manager.speaker = speaker
        self.home.integration_prefs["voice_wake"] = True
        self.home.integration_prefs["voice_microphone"] = True
        self.manager.restart_wake = True
        self.manager.start = MagicMock()
        self.manager.set_state("speaking")
        callbacks=[]
        with patch("home_voice.QTimer.singleShot", side_effect=lambda ms, cb: callbacks.append((ms, cb))):
            self.manager.speech_finished(speaker)
        self.assertEqual(self.eyes.voice_state, "")
        self.manager.start.assert_not_called()
        self.assertEqual(len(callbacks), 1)
        self.assertGreaterEqual(callbacks[0][0], 500)
        callbacks[0][1]()
        self.manager.start.assert_called_once_with("wake")


if __name__ == "__main__":
    unittest.main()
