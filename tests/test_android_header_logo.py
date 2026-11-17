"""Ensure the HOME Android header uses the approved static app image."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "android/app/src/main/java/com/aqnoeu/home/MainActivity.java"
EYES = ROOT / "android/app/src/main/java/com/aqnoeu/home/EyesView.java"
LOGO = ROOT / "android/app/src/main/res/drawable-nodpi/home_header_eyes.png"


class AndroidHeaderLogoTest(unittest.TestCase):
    def test_header_uses_static_official_app_icon(self):
        main = MAIN.read_text(encoding="utf-8")
        section = main.split("LinearLayout brand=new LinearLayout(this);", 1)[1].split(
            "LinearLayout brandCopy=column();", 1
        )[0]
        self.assertIn("ImageView brandIcon=new ImageView(this);", section)
        self.assertIn("brandIcon.setImageResource(R.drawable.home_header_eyes);", section)
        self.assertIn("brandIcon.setScaleType(ImageView.ScaleType.FIT_CENTER);", section)
        self.assertIn("brand.addView(brandIcon,iconSize);", section)
        self.assertNotIn("EyesView", section)
        self.assertIn("iconSize.rightMargin=dp(10);", section)
        self.assertIn("LinearLayout.LayoutParams(dp(58),dp(48))", section)
        self.assertIn("brandIcon.setBackground(null);", section)

    def test_transparent_png_exists(self):
        import struct
        data = LOGO.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        # Image must have a transparency chunk instead of the solid launcher background.
        self.assertIn(b"tRNS", data)
        self.assertGreater(struct.unpack(">I", data[16:20])[0], 24)

    def test_expression_labels_do_not_wrap(self):
        main = MAIN.read_text(encoding="utf-8")
        # O seletor novo usa grade 2x3, sem rolagem horizontal.
        self.assertIn("b.setSingleLine(true);", main)
        self.assertIn("final int columns=3, rows=2, perPage=columns*rows;", main)
        self.assertIn("addExpressionPicker(face,eyes,prefs);", main)
        self.assertNotIn("dp(labels[i].equals(\"Sonolento\")?110:94)", main)

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
