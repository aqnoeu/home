"""Testes do download em blocos do atualizador."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from update_service import download_package


class FakeResponse:
    url = "https://release-assets.githubusercontent.com/example"
    def __init__(self, content):
        self.content = content
        self.offset = 0
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, n):
        block = self.content[self.offset:self.offset+n]
        self.offset += len(block)
        return block


class TestDownloadPackage(TestCase):
    def test_stream_and_sha256(self):
        data = b"home" * 1024
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "Home-Windows.zip"
            with patch("update_service.urllib.request.urlopen", return_value=FakeResponse(data)):
                digest = download_package("https://github.com/aqnoeu/home/releases/download/v1/Home-Windows.zip", dest, limit=len(data))
            self.assertEqual(dest.read_bytes(), data)
            self.assertEqual(digest, hashlib.sha256(data).hexdigest())

    def test_size_limit(self):
        data = b"x" * 1025
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "Home-Windows.zip"
            with patch("update_service.urllib.request.urlopen", return_value=FakeResponse(data)):
                with self.assertRaisesRegex(ValueError, "excede o limite"):
                    download_package("https://github.com/aqnoeu/home/releases/download/v1/Home-Windows.zip", dest, limit=1024)
