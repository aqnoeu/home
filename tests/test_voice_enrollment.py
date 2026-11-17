import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import home_voice_profile as profile


class VoiceEnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path_patch = patch.object(profile, "PROFILE", Path(self.tmp.name) / "voice.json")
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.tmp.cleanup()

    def test_call_only_and_call_with_function_are_distinct(self):
        self.assertTrue(profile.matches(0, "Ei Home"))
        self.assertTrue(profile.matches(1, "Ok Home"))
        self.assertTrue(profile.matches(2, "Home"))
        self.assertFalse(profile.matches(3, "Ei Home"))
        self.assertTrue(profile.matches(3, "Ei Home, que horas são?"))
        self.assertTrue(profile.matches(4, "Ok Home que dia é hoje"))
        self.assertTrue(profile.matches(5, "Home qual a bateria do computador"))

    def test_punctuation_and_double_spaces_do_not_break_matching(self):
        self.assertEqual(profile.normalize("Ok,  Home!"), "ok home")
        self.assertTrue(profile.matches(1, "Ok, Home"))
        self.assertTrue(profile.matches(4, "Ok, Home,  que dia é hoje?"))

    def test_reviewed_correction_only(self):
        self.assertEqual(profile.wake_suffix("ei rome"), None)
        profile.accept("ei rome", corrected=True)
        self.assertEqual(profile.wake_suffix("ei rome que horas sao"), "que horas sao")
        self.assertEqual(profile.wake_suffix("palavra ei rome"), None)

    def test_reset_erases_corrected_aliases(self):
        profile.accept("ei rome", corrected=True)
        profile.reset()
        self.assertEqual(profile.load()["step"], 0)
        self.assertEqual(profile.wake_suffix("ei rome"), None)


if __name__ == "__main__":
    unittest.main()
