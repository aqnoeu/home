"""Keep the two HOME apps aligned without mixing platform-native APIs."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PlatformParityTests(unittest.TestCase):
    def test_same_chat_model_and_json_contract(self):
        android = (ROOT / "android/app/src/main/java/com/aqnoeu/home/HomeGroq.java").read_text(encoding="utf-8")
        desktop = (ROOT / "home_groq_client.py").read_text(encoding="utf-8")
        self.assertIn('openai/gpt-oss-20b', android)
        self.assertIn('openai/gpt-oss-20b', desktop)
        self.assertIn('https://api.groq.com/openai/v1/chat/completions', android)
        self.assertIn('https://api.groq.com/openai/v1/chat/completions', desktop)
        self.assertIn('json_object', android)
        self.assertIn('json_object', desktop)
        for field in ("resposta", "emocao"):
            self.assertIn(field, android)
            self.assertIn(field, desktop)

    def test_neither_app_embeds_a_private_groq_key(self):
        desktop = (ROOT / "home_groq.py").read_text(encoding="utf-8")
        android = (ROOT / "android/app/src/main/java/com/aqnoeu/home/HomeGroq.java").read_text(encoding="utf-8")
        gradle = (ROOT / "android/app/build.gradle.kts").read_text(encoding="utf-8")
        self.assertNotIn("home_groq_builtin", desktop)
        self.assertNotIn("BuildConfig.HOME_GROQ_API_KEY", android)
        self.assertNotIn('buildConfigField("String", "HOME_GROQ_API_KEY"', gradle)
        self.assertIn("keyring.get_password", desktop)
        self.assertIn("AndroidKeyStore", android)

    def test_one_version_and_one_release_with_both_artifacts(self):
        workflow = (ROOT / ".github/workflows/home-release.yml").read_text(encoding="utf-8")
        android_gradle = (ROOT / "android/app/build.gradle.kts").read_text(encoding="utf-8")
        android_updater = (ROOT / "android/app/src/main/java/com/aqnoeu/home/UpdateHelper.java").read_text(encoding="utf-8")
        self.assertIn("HOME_RELEASE_VERSION", workflow)
        self.assertIn("HOME_RELEASE_VERSION", android_gradle)
        self.assertIn("needs: [version, windows, android]", workflow)
        self.assertIn("Home-Windows.zip", workflow)
        self.assertIn("Home-Android.apk", workflow)
        self.assertIn('tag.substring(1)', android_updater)
        self.assertNotIn('android-v\\\\d+', android_updater)


if __name__ == "__main__":
    unittest.main()
