"""Local Windows and Android device connector regression checks."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import home_device

ROOT=Path(__file__).resolve().parents[1]
ANDROID=ROOT/"android/app/src/main/java/com/aqnoeu/home"
MAIN=(ANDROID/"MainActivity.java").read_text(encoding="utf-8")
DEVICE=(ANDROID/"DeviceHub.java").read_text(encoding="utf-8")
NOTIFICATIONS=(ANDROID/"HomeNotifications.java").read_text(encoding="utf-8")
MANIFEST=(ROOT/"android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")

class DeviceConnectorTests(unittest.TestCase):
    def test_local_diagnostics_do_not_execute_external_commands(self):
        self.assertIsNone(home_device.local_query("execute powershell e delete arquivos"))
        self.assertTrue(home_device.local_query("bateria notebook"))
        self.assertIn("RAM",home_device.local_query("memoria ram"))
        self.assertTrue(home_device.local_query("espaco livre"))
        self.assertIsNone(home_device.local_query("pesquise na internet"))

    def test_windows_panels_allowlist(self):
        self.assertNotIn("powershell",home_device.SYSTEM_PANELS)
        self.assertIn("bluetooth_settings",home_device.SYSTEM_PANELS)
        with self.assertRaises(ValueError):
            home_device.open_panel("cmd.exe /c whoami")

    def test_android_queries_and_permissions(self):
        self.assertIn("NET_CAPABILITY_VALIDATED",DEVICE)
        self.assertIn("BLUETOOTH_CONNECT",DEVICE)
        self.assertIn("getAvailableBytes()",DEVICE)
        self.assertIn("getMemoryInfo(info)",DEVICE)
        self.assertIn("getDevices(AudioManager.GET_DEVICES_OUTPUTS)",DEVICE)
        self.assertIn('android.permission.READ_CALENDAR',MANIFEST)
        self.assertIn('android.permission.ACCESS_NETWORK_STATE',MANIFEST)
        self.assertIn('android.permission.BLUETOOTH_CONNECT',MANIFEST)
        self.assertIn("private void showTodayEvents()",MAIN)
        self.assertIn("requestPermissions(new String[]{Manifest.permission.READ_CALENDAR}",MAIN)

    def test_notifications_opt_in_no_cloud_or_storage(self):
        self.assertIn("BIND_NOTIFICATION_LISTENER_SERVICE",MANIFEST)
        self.assertIn("ACTION_NOTIFICATION_LISTENER_SETTINGS",MAIN)
        self.assertIn("requestInlineConfirm",MAIN)
        self.assertIn("NotificationListenerService",NOTIFICATIONS)
        self.assertIn("getActiveNotifications()",NOTIFICATIONS)
        self.assertIn("RemoteInput.addResultsToIntent",NOTIFICATIONS)
        self.assertNotIn("HomeGroq",NOTIFICATIONS)
        self.assertNotIn("SharedPreferences",NOTIFICATIONS)
        self.assertNotIn("getActiveNotifications()",MAIN)
        self.assertIn("Ver texto copiado (somente agora)",MAIN)

if __name__=="__main__":
    unittest.main()
