"""Testes do motor de fala Kokoro sem baixar modelos ou reproduzir áudio."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from home_kokoro import (
    VOICE, MODEL_URLS, MIN_SIZES, installed, speed_from_rate,
    synthesize, KokoroDownloadWorker
)


class KokoroTests(unittest.TestCase):
    def test_alex_is_portuguese_voice(self):
        self.assertEqual(VOICE, "pm_alex")
        self.assertEqual(set(MODEL_URLS), {"kokoro-v1.0.onnx", "voices-v1.0.bin"})

    def test_never_claims_installed_for_missing_files(self):
        with tempfile.TemporaryDirectory() as location:
            self.assertFalse(installed(Path(location)))

    def test_incomplete_model_is_not_installed(self):
        with tempfile.TemporaryDirectory() as location:
            root = Path(location)
            for name in MODEL_URLS:
                (root / name).write_bytes(b"truncated")
            self.assertFalse(installed(root))

    def test_speed_mapping_is_bounded(self):
        self.assertEqual(speed_from_rate(165), 1.0)
        self.assertLess(speed_from_rate(90), 1.0)
        self.assertGreater(speed_from_rate(280), 1.0)
        self.assertLessEqual(speed_from_rate(999), 1.3)

    def test_synthesis_requires_opt_in_download(self):
        with tempfile.TemporaryDirectory() as location:
            with self.assertRaises(FileNotFoundError):
                synthesize("Olá!", root=Path(location))

    def test_worker_does_not_download_when_already_installed(self):
        with patch("home_kokoro.installed", return_value=True):
            worker = KokoroDownloadWorker()
            events=[]
            worker.completed.connect(lambda: events.append("ready"))
            worker.run()
            self.assertEqual(events, ["ready"])


if __name__ == "__main__":
    unittest.main()
