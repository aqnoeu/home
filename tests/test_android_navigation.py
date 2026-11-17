"""HOME mobile UX: conversation first, history and direct settings switches."""
from pathlib import Path
import unittest

SRC = (Path(__file__).resolve().parents[1] /
       "android/app/src/main/java/com/aqnoeu/home/MainActivity.java")


class MobileNavigationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = SRC.read_text(encoding="utf-8")

    def test_conversation_is_initial_page(self):
        self.assertIn('VoiceCleanup.cleanup(this);\n        showPage("assistant");', self.code)
        self.assertNotIn('VoiceCleanup.cleanup(this);\n        showHub();', self.code)

    def test_only_three_primary_destinations(self):
        self.assertIn('String[] routes={"assistant","history","settings"};', self.code)
        self.assertIn('private void showHistory()', self.code)
        self.assertIn('private void showSettings(String tab)', self.code)

    def test_settings_tabs_are_inline(self):
        self.assertIn('String[] names={"Geral","Voz / IA","Aparência","Conta HOME"};', self.code)
        for text in ['"Mostrar notch"', '"Ouvir ‘Ei, Home’"', '"Mostrar aba de toque"',
                     '"Integrar à barra superior"', '"Responder com voz"']:
            self.assertIn(text, self.code)
        self.assertIn('private Switch settingSwitch(', self.code)

    def test_updates_are_compact(self):
        self.assertIn('refresh.setContentDescription("Verificar atualizações");', self.code)
        self.assertIn('UpdateHelper.check(this,status);', self.code)

    def test_preserve_chat_and_static_official_logo(self):
        self.assertIn('HomeChatStore.get(this).newChat();', self.code)
        self.assertIn('renderChatList();', self.code)
        self.assertIn('logo.setImageResource(R.drawable.home_header_eyes);', self.code)
        self.assertIn('brandIcon.setImageResource(R.drawable.home_header_eyes);', self.code)
        self.assertIn('EyesView eyes=new EyesView(this);', self.code)


if __name__ == "__main__":
    unittest.main()
