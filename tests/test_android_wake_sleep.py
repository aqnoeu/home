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

    def test_prefer_local_recognition_and_no_partial_result_triggers(self):
        wake = (SRC / "WakeWordService.java").read_text(encoding="utf-8")
        self.assertIn('SpeechRecognizer.isOnDeviceRecognitionAvailable(this)', wake)
        self.assertIn('SpeechRecognizer.createOnDeviceSpeechRecognizer(this)', wake)
        self.assertIn('RecognizerIntent.EXTRA_PREFER_OFFLINE,true', wake)
        self.assertIn('RecognizerIntent.EXTRA_PARTIAL_RESULTS,false', wake)
        self.assertIn('String[] triggers={"ei home","hey home","oi home","ok home"}', wake)
        self.assertIn('if(!paused)detect(b);', wake)


if __name__ == "__main__":
    unittest.main()
