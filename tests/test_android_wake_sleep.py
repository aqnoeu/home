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

    def test_voice_animation_shows_actual_microphone_state(self):
        wake=(SRC/"WakeWordService.java").read_text(encoding="utf-8")
        eyes=(SRC/"EyesView.java").read_text(encoding="utf-8")
        self.assertIn('visualState("detector_ativo")',wake)
        self.assertNotIn('visualState("ouvindo")',wake)
        self.assertIn('showCommandListening(Context context)',wake)
        self.assertIn('showProcessing(Context context)',wake)
        self.assertIn('visualState("aguardando_comando")',wake)
        self.assertIn('visualState("falando")',wake)
        self.assertIn('visualState("desligado")',wake)
        self.assertIn('wake_visual_state',eyes)
        self.assertIn('boolean passiveWake="detector_ativo".equals(voice)',eyes)
        self.assertIn('if(commandListening){',eyes)
        self.assertIn('speaking || passiveWake',eyes)
        self.assertNotIn('boolean listening="ouvindo"',eyes)
        self.assertIn('commandListening',eyes)
        self.assertIn('Color.rgb(45,255,90)',eyes)
        self.assertIn('rgb=Color.WHITE',eyes)
        self.assertIn('verde-neon, expressão feliz',eyes)
        self.assertNotIn('paint.setColor(commandListening?',eyes)
        self.assertIn('float speakingPulse=speaking&&animated',eyes)
        self.assertIn('if(speaking){',eyes)
        self.assertIn('i<3',eyes)

    def test_background_faber_opt_in_and_recovery(self):
        wake=(SRC/"WakeWordService.java").read_text(encoding="utf-8")
        faber=(SRC/"FaberOffline.kt").read_text(encoding="utf-8")
        activity=(SRC/"MainActivity.java").read_text(encoding="utf-8")
        self.assertIn('wake_background_audio',wake)
        self.assertIn('speakBackground(this,answer',wake)
        self.assertIn('backgroundCommandTimeout',wake)
        self.assertIn('pendingNotificationRecovery',wake)
        self.assertIn('consecutiveAudioErrors',wake)
        self.assertIn('audioGeneration',wake)
        self.assertIn('wake_background_audio',activity)
        self.assertIn('WakeWordService.showCommandListening(this);',activity)
        self.assertIn('if(request==HomeVoice.REQUEST_SPEECH)WakeWordService.showProcessing(this);',activity)
        self.assertIn('fun speakBackground(context: Context',faber)

    def test_offline_vosk_activation_with_stable_partial_confirmation(self):
        wake = (SRC / "WakeWordService.java").read_text(encoding="utf-8")
        self.assertIn("import org.vosk.Model;", wake)
        self.assertIn("import org.vosk.android.SpeechService;", wake)
        self.assertIn("new Model(WakeModelInstaller.folder(this).getAbsolutePath())", wake)
        self.assertIn("new SpeechService(recognizer,16000.0f)", wake)
        self.assertIn("audio.startListening(sessionListener)", wake)
        self.assertIn('String[] prefix={"ei home","ok home","hey home","oi home"', wake)
        self.assertIn("onPartialResult(String hypothesis){detect(hypothesis,true);}", wake)
        self.assertIn("partialCount<3", wake)
        self.assertIn("now-partialSince<200", wake)
        self.assertIn("home ok home", wake)
        self.assertIn("MainActivity.isInForeground()", wake)
        self.assertIn("home_wake_detected_v2", wake)
        self.assertIn("onResult(String hypothesis){detect(hypothesis,false);}", wake)
        self.assertIn("closeAudio(); // libera o AudioRecord", wake)
        self.assertNotIn("SpeechRecognizer.createSpeechRecognizer", wake)


if __name__ == "__main__":
    unittest.main()
