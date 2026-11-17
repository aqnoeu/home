"""Regression contracts for HOME Intersect's incremental modularization.

Static checks are deliberately small: Android compilation and existing UI/voice
behavior are independently verified by the platform workflows.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
ANDROID=ROOT/"android/app/src/main/java/com/aqnoeu/home"


class ModularArchitectureTest(unittest.TestCase):
    def test_windows_eyes_have_one_rendering_owner(self):
        main=(ROOT/"home.py").read_text(encoding="utf-8")
        eyes=(ROOT/"home_eyes.py").read_text(encoding="utf-8")
        self.assertIn("from home_eyes import EyesWidget",main)
        self.assertNotIn("class EyesWidget(QWidget):",main)
        self.assertIn("class EyesWidget(QWidget):",eyes)
        self.assertIn("def paintEvent(self, event):",eyes)
        self.assertIn("def blink_on_click(self, now=None):",eyes)

    def test_windows_edit_dialog_has_one_owner(self):
        main=(ROOT/"home.py").read_text(encoding="utf-8")
        editor=(ROOT/"home_edit_dialog.py").read_text(encoding="utf-8")
        self.assertIn("from home_edit_dialog import EditDialog",main)
        self.assertNotIn("class EditDialog(QDialog):",main)
        self.assertIn("class EditDialog(QDialog):",editor)
        self.assertIn("def sync(self):",editor)

    def test_android_ui_kit_keeps_existing_colors_and_root_binding(self):
        main=(ANDROID/"MainActivity.java").read_text(encoding="utf-8")
        kit=(ANDROID/"HomeUiKit.java").read_text(encoding="utf-8")
        self.assertIn("private final HomeUiKit ui=new HomeUiKit(this);",main)
        self.assertIn("ui.setRoot(root);",main)
        self.assertIn("public LinearLayout card(String title,String description)",kit)
        self.assertIn("public EditText edit(String hint,boolean secret)",kit)
        self.assertIn("Color.rgb(47,107,255)",kit)
        self.assertIn("b.setMinHeight(dp(48));",kit)

    def test_local_commands_do_not_execute_actions_directly(self):
        main=(ANDROID/"MainActivity.java").read_text(encoding="utf-8")
        commands=(ANDROID/"HomeLocalCommands.java").read_text(encoding="utf-8")
        self.assertIn("HomeLocalCommands.resolve(this,query)",main)
        self.assertIn("if(setting!=null)openDeviceSettings(setting)",main)
        self.assertIn("if(speak)speakAnswer(answer)",main)
        self.assertIn("public static Result resolve(Context context,String query)",commands)
        self.assertNotIn("startActivity(",commands)
        self.assertNotIn("HomeChatStore",commands)
        self.assertNotIn("HomeGroq",commands)

    def test_future_plan_saved_in_repository(self):
        roadmap=(ROOT/"docs/HOME_EVOLUTION_ROADMAP.md").read_text(encoding="utf-8")
        architecture=(ROOT/"docs/HOME_ARCHITECTURE.md").read_text(encoding="utf-8")
        for name in ("OpenDex","PILLAR","Sherpa-ONNX","Xiaozhi","Troko-Desk"):
            self.assertIn(name,roadmap)
        self.assertIn("HomeLocalCommands.java",architecture)
        self.assertIn("home_eyes.py",architecture)


if __name__=="__main__":
    unittest.main()
