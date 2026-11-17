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
        self.assertIn('visualState("armado")',wake)
        self.assertIn('visualState("aguardando_comando")',wake)
        self.assertIn('visualState("falando")',wake)
        self.assertIn('visualState("desligado")',wake)
        self.assertIn('wake_visual_state',eyes)
        self.assertIn('commandListening',eyes)
        self.assertIn('boolean listening="aguardando_comando".equals(voice)',eyes)
        self.assertIn('boolean armed="armado".equals(voice)',eyes)
        self.assertIn('Color.rgb(45,255,90)',eyes)
        self.assertIn('rgb=Color.WHITE',eyes)
        self.assertIn('verde-neon, expressão feliz',eyes)
        self.assertNotIn('paint.setColor(commandListening?',eyes)
        self.assertIn('float speakingPulse=speaking&&animated',eyes)
        self.assertIn('if(speaking && !updateActive){',eyes)
        self.assertIn('i<3',eyes)

    def test_download_eyes_use_verified_real_progress_and_single_wink(self):
        updater=(SRC/"UpdateHelper.java").read_text(encoding="utf-8")
        eyes=(SRC/"EyesView.java").read_text(encoding="utf-8")
        self.assertIn('total*100L/size',updater)
        self.assertIn('Math.min(99L',updater)
        self.assertIn('if (!actual.toString().equals(digest))',updater)
        self.assertIn('updateEyes(activity,"complete",100)',updater)
        self.assertIn('updateEyes(activity,"idle",0)',updater)
        self.assertIn('update_eyes_percent',eyes)
        self.assertIn('Color.rgb(139,149,164)',eyes)
        self.assertIn('paint.setColor(Color.WHITE)',eyes)
        self.assertIn('mask.addRoundRect(eyeBounds',eyes)
        self.assertIn('if(updateComplete && i==1',eyes)
        self.assertIn('updateElapsed<2600L',eyes)
        self.assertIn('registerOnSharedPreferenceChangeListener(updateListener)',eyes)
        self.assertIn('updateElapsed>=700 && updateElapsed<1150',eyes)
        self.assertNotIn('updateElapsed>=210 && updateElapsed<610',eyes)

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
        self.assertIn('captureBackgroundCommand(text,partial)',wake)
        self.assertIn('store.addTo(session,"user",command)',wake)
        self.assertIn('store.addTo(session,"assistant",answer)',wake)
        self.assertIn('main.postDelayed(completePendingCommand,partial?1400L:100L)',wake)
        self.assertIn('getBooleanExtra("command_listening",false)',wake)
        self.assertIn('wake_background_audio',activity)
        self.assertIn('fun speakBackground(context: Context',faber)

    def test_background_voice_saves_dialog_before_notifying(self):
        wake=(SRC/"WakeWordService.java").read_text(encoding="utf-8")
        activity=(SRC/"MainActivity.java").read_text(encoding="utf-8")
        self.assertIn('if(!MainActivity.isInForeground()){',wake)
        self.assertIn('beginBackgroundConversation(command);',wake)
        self.assertIn('store.addTo(session,"user",command);',wake)
        self.assertIn('store.addTo(session,"assistant",answer);',wake)
        self.assertIn('notifyBackgroundAnswer(command,answer);',wake)
        self.assertIn('if(!backgroundVoiceEnabled()){',wake)
        self.assertIn('private void resumeBackgroundListening()',wake)
        self.assertIn('if("assistant".equals(currentPage))refreshChat();',activity)
        # No longer notify just because the wake word was heard in background.
        self.assertNotIn('if(!MainActivity.isInForeground() && backgroundVoiceEnabled())',wake)

    def test_offline_vosk_activation_with_stable_partial_confirmation(self):
        wake = (SRC / "WakeWordService.java").read_text(encoding="utf-8")
        self.assertIn("import org.vosk.Model;", wake)
        self.assertIn("import org.vosk.android.SpeechService;", wake)
        self.assertIn("new Model(WakeModelInstaller.folder(this).getAbsolutePath())", wake)
        self.assertIn("new SpeechService(recognizer,16000.0f)", wake)
        self.assertIn("audio.startListening(sessionListener)", wake)
        self.assertIn('String[] prefix={"ei home","ok home","hey home","oi home"', wake)
        self.assertIn("onPartialResult(String hypothesis){detect(hypothesis,true);}", wake)
        self.assertIn("pendingWakeConfirmation", wake)
        self.assertIn("main.postDelayed(pendingWakeConfirmation,750L)", wake)
        self.assertIn("rememberHypothesis(text,partial)",wake)
        self.assertIn("wake_last_hypothesis",wake)
        self.assertIn("main.removeCallbacks(pendingWakeConfirmation)",wake)
        self.assertIn("home ok home", wake)
        self.assertIn("MainActivity.isInForeground()", wake)
        self.assertIn("home_wake_detected_v2", wake)
        self.assertIn("onResult(String hypothesis){detect(hypothesis,false);}", wake)
        self.assertIn("closeAudio(); // libera o AudioRecord", wake)
        self.assertNotIn("SpeechRecognizer.createSpeechRecognizer", wake)


if __name__ == "__main__":
    unittest.main()
