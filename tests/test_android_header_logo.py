"""Prevent accidental replacement of the HOME Android header eyes with a flat icon."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "android/app/src/main/java/com/aqnoeu/home/MainActivity.java"
EYES = ROOT / "android/app/src/main/java/com/aqnoeu/home/EyesView.java"


class AndroidHeaderLogoTest(unittest.TestCase):
    def test_header_reuses_existing_eyes_view(self):
        main = MAIN.read_text(encoding="utf-8")
        section = main.split("LinearLayout brand=new LinearLayout(this);", 1)[1].split(
            "LinearLayout brandCopy=column();", 1
        )[0]
        self.assertIn("EyesView brandEyes=new EyesView(this);", section)
        self.assertIn("brand.addView(brandEyes,iconSize);", section)
        self.assertNotIn("home_icon_approved", section)
        self.assertIn("iconSize.rightMargin=dp(6);", section)
        self.assertIn("LinearLayout.LayoutParams(dp(72),dp(48))", section)

    def test_header_copy_and_expression_view_remain(self):
        main = MAIN.read_text(encoding="utf-8")
        self.assertIn('heading("HOME",21)', main)
        self.assertIn('note("Um assistente para você.")', main)
        self.assertIn("EyesView eyes=new EyesView(this);", main)
        self.assertIn("face.addView(eyes,eyesSize);", main)
        self.assertIn("public final class EyesView extends View",
                      EYES.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
