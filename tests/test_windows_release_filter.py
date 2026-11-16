"""Windows Home updates must not be confused with Android releases."""
import json
import unittest
from unittest.mock import patch
import update_service


class WindowsReleaseFilterTests(unittest.TestCase):
    def test_skips_android_and_chooses_windows(self):
        releases=[
            {"tag_name":"android-v0.1.3", "assets":[{"name":"Home-Android.apk","browser_download_url":"https://github.com/aqnoeu/home/releases/download/android-v0.1.3/Home-Android.apk"}]},
            {"tag_name":"v0.7.22", "assets":[
                {"name":"Home-Windows.zip","browser_download_url":"https://github.com/aqnoeu/home/releases/download/v0.7.22/Home-Windows.zip"},
                {"name":"SHA256SUMS.txt","browser_download_url":"https://github.com/aqnoeu/home/releases/download/v0.7.22/SHA256SUMS.txt"}
            ]}
        ]
        with patch("update_service.fetch",return_value=json.dumps(releases).encode()):
            data=update_service.release_info()
        self.assertEqual(data["version"],"v0.7.22")

    def test_no_windows_assets(self):
        with patch("update_service.fetch",return_value=b'[{"tag_name":"android-v0.1.3","assets":[]}]'):
            self.assertIsNone(update_service.release_info())


if __name__=="__main__":
    unittest.main()
