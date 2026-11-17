"""Tests for the shared HOME account (no network calls)."""
import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class AccountIntegrationTests(unittest.TestCase):
    def test_windows_code_parses(self):
        ast.parse((ROOT/"home_account.py").read_text(encoding="utf-8"))
    def test_windows_workspace_renders_account(self):
        source=(ROOT/"home_navigation.py").read_text(encoding="utf-8")
        self.assertIn('("account","♙ Conta HOME")',source)
        self.assertIn('from home_account import AccountPage',source)
    def test_android_opt_in_and_keystore(self):
        source=(ROOT/"android/app/src/main/java/com/aqnoeu/home/HomeHubAccount.java").read_text(encoding="utf-8")
        self.assertIn('AndroidKeyStore',source)
        self.assertIn('sync_chats',source)
        self.assertIn('resolution=ignore-duplicates',source)
        self.assertIn('public synchronized int uploadLocalChats',source)
    def test_no_cloud_remote_commands(self):
        windows=(ROOT/"home_account.py").read_text(encoding="utf-8")
        android=(ROOT/"android/app/src/main/java/com/aqnoeu/home/HomeHubAccount.java").read_text(encoding="utf-8")
        self.assertNotIn('exec(',windows)
        self.assertNotIn('Runtime.getRuntime().exec(',android)
if __name__=="__main__":unittest.main()
