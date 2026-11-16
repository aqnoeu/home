"""Regressão: voz Faber instalada localmente, sem servidor e sem cobrança."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from home_faber import VOICE, MODEL_NAME, MODEL_SHA256, installed, synthesize, FaberDownloadWorker


class FaberTests(unittest.TestCase):
    def test_model_identity(self):
        self.assertEqual(VOICE, "pt_BR-faber-medium")
        self.assertEqual(MODEL_NAME, "vits-piper-pt_BR-faber-medium")
        self.assertEqual(MODEL_SHA256, "7add3f923ad6bc25ca8a192805fd1a64d1b3893e4611c4a9719545a825039a83")

    def test_missing_model_not_installed(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(installed(temp))
            with self.assertRaises(FileNotFoundError):
                synthesize("Olá", root=temp)

    def test_truncated_model_not_installed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"pt_BR-faber-medium.onnx").write_bytes(b"incompleto")
            (root/"tokens.txt").write_text("a"*250,encoding="utf-8")
            (root/"espeak-ng-data").mkdir()
            self.assertFalse(installed(root))

    def test_installed_short_circuits_download(self):
        with patch("home_faber.installed", return_value=True):
            worker=FaberDownloadWorker()
            completed=[]
            worker.completed.connect(lambda:completed.append(True))
            worker.run()
            self.assertEqual(completed,[True])


if __name__ == "__main__":
    unittest.main()
