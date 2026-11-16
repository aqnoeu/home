"""Regression checks for Android sleep marks and voice activation behavior."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "android/app/src/main/java/com/aqnoeu/home"


class AndroidWakeSleepTest(unittest.TestCase):
    def test_small_notch_draws_sleep_z(self):
        eyes = (SRC / "EyesView.java").read_text(encoding="utf-8")
        self.assertIn('height>=dp(20)', eyes)
        self.assertNotIn('height>=dp(68)', eyes)
        self.assertIn('canvas.drawText("z"', eyes)
        self.assertIn('float scale=', eyes)

    def test_notch_background_remains_dark_and_opaque(self):
        overlay = (SRC / "OverlayService.java").read_text(encoding="utf-8")
        self.assertIn('bg.setColor(Color.rgb(11,17,26));', overlay)
        self.assertIn('eyes.setBackground(bg);', overlay)

    def test_offline_vosk_activation_without_partial_triggers(self):
        wake = (SRC / "WakeWordService.java").read_text(encoding="utf-8")
        self.assertIn("import org.vosk.Model;", wake)
        self.assertIn("import org.vosk.android.SpeechService;", wake)
        self.assertIn("new Model(WakeModelInstaller.folder(this).getAbsolutePath())", wake)
        self.assertIn("new SpeechService(recognizer,16000.0f)", wake)
        self.assertIn("audio.startListening(this)", wake)
        self.assertIn('String[] triggers={"ei home","ok home","hey home","oi home"', wake)
        self.assertIn("onPartialResult(String hypothesis){}", wake)
        self.assertIn("onResult(String hypothesis){detect(hypothesis);}", wake)
        self.assertIn("closeAudio(); // libera o AudioRecord", wake)
        self.assertNotIn("SpeechRecognizer.createSpeechRecognizer", wake)


if __name__ == "__main__":
    unittest.main()
