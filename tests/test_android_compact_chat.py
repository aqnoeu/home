"""Regression checks for compact HOME Android chat on narrow devices."""
from pathlib import Path
import unittest

MAIN = (Path(__file__).resolve().parents[1] /
    "android/app/src/main/java/com/aqnoeu/home/MainActivity.java")

class CompactChatLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = MAIN.read_text(encoding="utf-8")

    def test_compact_header_and_one_line_status(self):
        source = self.code
        self.assertIn('"● Conectado":"● Sem conexão"', source)
        self.assertIn('state.setSingleLine(true);', source)
        self.assertNotIn('toque para configurar"', source)
        self.assertIn('logo.setImageResource(R.drawable.home_header_eyes);', source)
        self.assertIn('top.addView(refresh,new LinearLayout.LayoutParams(dp(40),dp(44)));', source)

    def test_history_is_not_duplicated_in_header(self):
        chat = self.code.split('private void assistantPage(){', 1)[1].split(
            'private void showConnectionSettings(', 1)[0]
        self.assertNotIn('Button history=button("Histórico', chat)
        self.assertIn('chatTitle.setSingleLine(true);', chat)
        self.assertIn('bottomNavigation("assistant")', chat)

    def test_messages_fit_small_width(self):
        self.assertIn('TextView body=text(message,14,WHITE,false);', self.code)
        self.assertIn('getResources().getConfiguration().screenWidthDp*0.82f', self.code)
        self.assertIn('body.setPadding(dp(12),dp(9),dp(12),dp(9));', self.code)

    def test_input_and_bottom_nav_held_at_screen_bottom(self):
        self.assertIn('shell.addView(chatScroll,new LinearLayout.LayoutParams(-1,0,1f));', self.code)
        self.assertIn('new LinearLayout.LayoutParams(-1,dp(50))', self.code)
        self.assertIn('chatInput.setTextSize(14);', self.code)

if __name__ == "__main__":
    unittest.main()
