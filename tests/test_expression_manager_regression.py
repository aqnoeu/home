"""Regression guards for HOME's Android and Windows expression wiring."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android/app/src/main/java/com/aqnoeu/home"


class ExpressionManagerRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.android_eyes = (ANDROID / "EyesView.java").read_text(encoding="utf-8")
        cls.android_emotions = (ANDROID / "HomeEmotion.java").read_text(encoding="utf-8")
        cls.android_ui = (ANDROID / "MainActivity.java").read_text(encoding="utf-8")
        cls.windows_eyes = (ROOT / "home_eyes.py").read_text(encoding="utf-8")
        cls.windows_app = (ROOT / "home.py").read_text(encoding="utf-8")
        cls.windows_gallery = (ROOT / "home_expression_gallery.py").read_text(encoding="utf-8")

    def test_android_selection_is_persisted_and_read_by_live_renderer(self):
        self.assertIn('putBoolean("expression_fixed",true)', self.android_ui)
        self.assertIn('preferences.getBoolean("expression_fixed",false)', self.android_emotions)
        self.assertIn('return chosen;', self.android_emotions)
        self.assertIn('HomeEmotion.current(getContext())', self.android_eyes)

    def test_android_x_hides_real_expression_and_restore_is_supported(self):
        self.assertIn('toggle.setChecked(false)', self.android_ui)
        self.assertIn('HomeEmotion.setEnabled(this,key,checked)', self.android_ui)
        self.assertIn('if(!checked)ensureValidSelectedExpression()', self.android_ui)
        self.assertIn('HomeEmotion.setEnabled(this,key,true)', self.android_ui)
        self.assertIn('visible.add(i)', self.android_ui)

    def test_android_preview_does_not_modify_global_manual_state(self):
        self.assertNotIn('HomeEmotion.manual(', self.android_eyes)
        self.assertIn('expressionPreview?EXPRESSION_KEYS[mood]:HomeEmotion.current(getContext())', self.android_eyes)

    def test_android_manual_holds_for_30_seconds_then_automatic_returns(self):
        self.assertIn('putLong("expression_selected_at",android.os.SystemClock.elapsedRealtime())', self.android_ui)
        self.assertIn('now-started<30000L', self.android_emotions)
        self.assertIn('putBoolean("expression_fixed",false)', self.android_emotions)
        self.assertLess(self.android_emotions.index('if(charging(context)'), self.android_emotions.index('if(preferences.getBoolean("expression_fixed"'))

    def test_windows_manual_holds_for_30_seconds_then_context_returns(self):
        self.assertIn('time.monotonic() + 30.0', self.windows_app)
        self.assertIn('def manual_expression_active(self):', self.windows_app)
        self.assertIn('self.settings["expression_fixed"] = False', self.windows_app)
        self.assertIn('if charging or low or saver:', self.windows_app)

    def test_sleepy_no_longer_renders_floating_z_or_blue_cheek_marks(self):
        self.assertNotIn('canvas.drawText("z"', self.android_eyes)
        self.assertNotIn('active == "sonolento" and h > 32:', self.windows_eyes)
        self.assertNotIn('if(("sonolento".equals(state)||"timido".equals(state))', self.android_eyes)
        self.assertIn('targetH=.38f', self.android_eyes)
        self.assertIn('"sonolento": (.40', self.windows_eyes)

    def test_windows_manager_controls_real_eyes_temporarily(self):
        self.assertIn('self.home.select_expression(index)', self.windows_gallery)
        self.assertIn('self.home.set_expression_visible(self.selected, False)', self.windows_gallery)
        self.assertIn('self.home.use_automatic_expressions()', self.windows_gallery)
        self.assertIn('self.apply_saved_expression()', self.windows_app)
        self.assertIn('self.settings["expression_fixed"] = True', self.windows_app)
        self.assertIn('self.save_settings()', self.windows_app)


if __name__ == "__main__":
    unittest.main()
