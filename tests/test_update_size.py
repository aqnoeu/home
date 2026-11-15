"""Regressão do atualizador: pacote Kokoro maior que 90 MiB."""
import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import update_service as service


class UpdatePackageTests(unittest.TestCase):
    def test_limit_is_larger_than_current_kokoro_release(self):
        self.assertGreaterEqual(service.LIMIT, 200 * 1024 * 1024)

    def test_valid_verified_archive_stages(self):
        with io.BytesIO() as stream:
            with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("Home.exe", b"Home")
                archive.writestr("HomeUpdater.exe", b"Updater")
            data = stream.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        manifest = (digest + "  Home-Windows.zip\n").encode("ascii")
        with patch.object(service, "fetch", side_effect=[data, manifest]):
            folder = service.stage_update({"zip": "test-zip", "sums": "test-sums"})
            try:
                self.assertEqual((folder / "Home.exe").read_bytes(), b"Home")
                self.assertEqual((folder / "HomeUpdater.exe").read_bytes(), b"Updater")
            finally:
                import shutil
                shutil.rmtree(folder, ignore_errors=True)

    def test_rejects_unexpected_files(self):
        with io.BytesIO() as stream:
            with zipfile.ZipFile(stream, "w") as archive:
                archive.writestr("Home.exe", b"Home")
                archive.writestr("HomeUpdater.exe", b"Updater")
                archive.writestr("extra.exe", b"extra")
            data = stream.getvalue()
        manifest = (hashlib.sha256(data).hexdigest() + "  Home-Windows.zip\n").encode("ascii")
        with patch.object(service, "fetch", side_effect=[data, manifest]):
            with self.assertRaisesRegex(ValueError, "inesperados"):
                service.stage_update({"zip": "test", "sums": "test"})


if __name__ == "__main__":
    unittest.main()
