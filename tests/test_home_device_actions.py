"""HOME mobile QR code and safe offline device actions."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/"android/app/src/main/java/com/aqnoeu/home/MainActivity.java").read_text(encoding="utf-8")
VOICE=(ROOT/"home_voice.py").read_text(encoding="utf-8")
INTEGRATIONS=(ROOT/"home_integrations.py").read_text(encoding="utf-8")

class DeviceActionsTest(unittest.TestCase):
    def test_qr_code_reachable_from_settings(self):
        self.assertIn('action(about,"Mostrar QR Code de download"',MAIN)
        self.assertIn('private void showDownloadQr(LinearLayout host)',MAIN)
        self.assertIn('matrix.get(x,y)?Color.BLACK:WHITE',MAIN)
        self.assertIn('"home-download-qr"',MAIN)

    def test_android_offline_commands_before_groq(self):
        main=MAIN.split('private void sendChatMessage(){',1)[1].split('private void bubble(',1)[0]
        self.assertLess(main.index('handleLocalCommand(q)'),main.index('HomeGroq.connected(this)'))
        self.assertIn('if(handleLocalCommand(question,true))return;',MAIN)
        wake=MAIN.split('private void handleWakeIntent(Intent intent){',1)[1].split('private void startWake(){',1)[0]
        self.assertLess(wake.index('handleLocalCommand(query,true)'),wake.index('askHome(query,null)'))
        self.assertIn('if(speak)speakAnswer(answer);',MAIN)
        self.assertIn('if(speak)resumeWake();',MAIN)
        self.assertIn('quantas horas',MAIN)
        self.assertIn('qual o horario',MAIN)
        self.assertIn('BatteryManager.EXTRA_LEVEL',MAIN)
        self.assertIn('Settings.ACTION_WIFI_SETTINGS',MAIN)
        self.assertIn('Settings.ACTION_BLUETOOTH_SETTINGS',MAIN)

    def test_windows_only_allowlisted_actions(self):
        self.assertIn('"taskmgr":',INTEGRATIONS)
        self.assertIn('"control_panel":',INTEGRATIONS)
        self.assertIn('return ("taskmgr",',VOICE)
        self.assertIn('return ("control_panel",',VOICE)
        self.assertIn('shell=False',INTEGRATIONS)

if __name__=="__main__": unittest.main()
