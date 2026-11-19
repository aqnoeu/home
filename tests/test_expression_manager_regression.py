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

    def test_android_preview_cannot_change_global_manual_expression(self):
        self.assertIn('if(!expressionPreview)HomeEmotion.manual', self.android_eyes)

    def test_sleepy_no_longer_renders_floating_z_or_blue_cheek_marks(self):
        self.assertNotIn('canvas.drawText("z"', self.android_eyes)
        self.assertNotIn('active == "sonolento" and h > 32:', self.windows_eyes)
        self.assertNotIn('if(("sonolento".equals(state)||"timido".equals(state))', self.android_eyes)
        self.assertIn('targetH=.38f', self.android_eyes)
        self.assertIn('"sonolento": (.40', self.windows_eyes)

    def test_windows_manager_controls_real_eyes_persistently(self):
        self.assertIn('self.home.select_expression(index)', self.windows_gallery)
        self.assertIn('self.home.set_expression_visible(index, False)', self.windows_gallery)
        self.assertIn('self.home.use_automatic_expressions()', self.windows_gallery)
        self.assertIn('self.apply_saved_expression()', self.windows_app)
        self.assertIn('self.settings["expression_fixed"] = True', self.windows_app)
        self.assertIn('self.save_settings()', self.windows_app)


if __name__ == "__main__":
    unittest.main()
