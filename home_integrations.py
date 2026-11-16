"""Integrações locais do Home: controles Windows e ponte de leitura opt-in do Chrome."""
import ctypes
import json
import shutil
import secrets
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from home_device import overview, open_panel, SYSTEM_PANELS
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QTextEdit, QMessageBox, QApplication
)

CONFIG_PATH = Path.home() / ".home_integrations.json"
MAX_BODY = 12000
PORT = 48731
COMMANDS = {
    "notepad": ("Bloco de Notas", ["notepad.exe"]),
    "calc": ("Calculadora", ["calc.exe"]),
    "explorer": ("Explorador de Arquivos", ["explorer.exe"]),
    "taskmgr": ("Gerenciador de Tarefas", ["taskmgr.exe"]),
    "control_panel": ("Painel de Controle", ["control.exe"]),
}
MEDIA_KEYS = {"volume_up": 0xAF, "volume_down": 0xAE, "mute": 0xAD,
              "play_pause": 0xB3, "next": 0xB0, "previous": 0xB1}


def load_preferences():
    base = {"eyes_follow_mouse": False, "eyes_react_clicks": False,
            "windows_controls": False, "chrome_reading": False,
            "voice_microphone": False, "voice_wake": False, "voice_speech": False,
            "voice_id": "", "voice_rate": 165, "voice_volume": 100,
            "voice_engine": "faber",
            "token": secrets.token_urlsafe(32)}
    try:
        source = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for key in base:
            if key == "token" and isinstance(source.get(key), str) and len(source[key]) >= 32:
                base[key] = source[key]
            elif key == "voice_engine":
                base[key] = "faber"
            elif key in ("voice_id",) and isinstance(source.get(key), str) and len(source[key]) < 512:
                base[key] = source[key]
            elif key == "voice_rate" and type(source.get(key)) is int and 90 <= source[key] <= 280:
                base[key] = source[key]
            elif key == "voice_volume" and type(source.get(key)) is int and 0 <= source[key] <= 100:
                base[key] = source[key]
            elif key != "token" and isinstance(source.get(key), bool):
                base[key] = source[key]
    except (OSError, ValueError, TypeError):
        pass
    return base


def save_preferences(prefs):
    CONFIG_PATH.write_text(json.dumps(prefs, indent=2), encoding="utf-8")


def cleanup_retired_voice():
    """One-time removal of only the retired Alex model; leave Vosk and other data."""
    import os
    root = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".local" / "share")) / "Home" / "models"
    target = root / "kokoro-v1.0"
    marker = root / ".alex_cleanup_v1"
    if marker.exists():
        return
    try:
        if target.is_dir():
            shutil.rmtree(target)
        root.mkdir(parents=True, exist_ok=True)
        marker.write_text("retired", encoding="utf-8")
    except OSError:
        pass


def execute_windows_action(action):
    if sys.platform != "win32":
        raise RuntimeError("Controles disponíveis somente no Windows.")
    if action in SYSTEM_PANELS:
        open_panel(action)
        return
    if action == "notifications_panel":
        # Win+N opens notification center on Windows 11, without reading content.
        user32 = ctypes.windll.user32
        for vk, flags in ((0x5B,0),(0x4E,0),(0x4E,2),(0x5B,2)):
            user32.keybd_event(vk,0,flags,0)
        return
    if action in COMMANDS:
        subprocess.Popen(COMMANDS[action][1], shell=False)
        return
    if action not in MEDIA_KEYS:
        raise ValueError("Ação não autorizada.")
    vk = MEDIA_KEYS[action]
    # teclas virtuais de mídia: sem comandos arbitrários ou acesso a arquivos
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk, 0, 0x0002, 0)


class ChromeBridge(QObject):
    received = Signal(str, str, str)
    error = Signal(str)

    def __init__(self, prefs):
        super().__init__()
        self.prefs = prefs
        self.server = None
        self._thread = None

    def start(self):
        if self.server:
            return
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def do_POST(self):
                if self.path != "/share":
                    return self.reply(404, "Rota inexistente")
                origin = self.headers.get("Origin", "")
                if not origin.startswith("chrome-extension://"):
                    return self.reply(403, "Origem não autorizada")
                if self.headers.get("X-Home-Token", "") != bridge.prefs["token"]:
                    return self.reply(403, "Código de conexão inválido")
                if not bridge.prefs.get("chrome_reading"):
                    return self.reply(403, "Leitura desativada no Home")
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    return self.reply(400, "Tamanho inválido")
                if not (0 < length <= MAX_BODY):
                    return self.reply(413, "Conteúdo muito grande")
                try:
                    body = json.loads(self.rfile.read(length))
                    title = body.get("title")
                    url = body.get("url")
                    content = body.get("text")
                    if not all(isinstance(v, str) for v in (title, url, content)):
                        return self.reply(400, "Dados inválidos")
                    if not url.startswith(("http://", "https://")):
                        return self.reply(400, "Página não permitida")
                    bridge.received.emit(title[:250], url[:2048], content[:5000])
                    return self.reply(200, "Compartilhado com o Home")
                except (ValueError, UnicodeError):
                    return self.reply(400, "Formato inválido")

            def reply(self, code, msg):
                data = json.dumps({"message": msg}, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", ""))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_OPTIONS(self):
                origin = self.headers.get("Origin", "")
                if not origin.startswith("chrome-extension://"):
                    self.send_response(403)
                    self.end_headers()
                    return
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Home-Token")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.end_headers()

        # Loopback somente: nenhuma porta exposta na rede local ou Internet.
        self.server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None


class IntegrationsDialog(QDialog):
    def __init__(self, home):
        super().__init__(home)
        self.home = home
        self.prefs = home.integration_prefs
        self.setWindowTitle("Home — Interações")
        self.setMinimumSize(420, 440)
        self.setStyleSheet("""
            QDialog {background:#0B111A;color:#FFFFFF;}
            QLabel,QCheckBox {color:#FFFFFF;}
            QPushButton {background:#292b2e;color:#eee;border:1px solid #324357;border-radius:9px;padding:9px;}
            QPushButton:hover {background:#26384F;}
            QTextEdit {background:#141D2A;color:#DDE7F4;border:1px solid #324357;border-radius:8px;}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16,18,16,16)
        layout.setSpacing(11)
        layout.addWidget(QLabel("Permissões e interações do HOME"))
        for key, caption in [
            ("eyes_follow_mouse", "Olhos acompanham o mouse"),
            ("eyes_react_clicks", "Olhos reagem a cliques"),
            ("windows_controls", "Permitir controles do Windows"),
            ("chrome_reading", "Receber páginas autorizadas do Chrome"),
        ]:
            box = QCheckBox(caption)
            box.setChecked(self.prefs[key])
            box.toggled.connect(lambda state,k=key: self.changed(k,state))
            layout.addWidget(box)

        layout.addWidget(QLabel("Windows — ações individuais (somente após clique)"))
        self.action_status = QLabel("")
        self.action_status.setWordWrap(True)
        layout.addWidget(self.action_status)
        buttons = QHBoxLayout()
        for key, label in [("notepad","Bloco de Notas"),("calc","Calculadora"),("explorer","Arquivos")]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, a=key: self.act(a))
            buttons.addWidget(button)
        layout.addLayout(buttons)
        media = QHBoxLayout()
        for key, label in [("volume_down","Volume −"),("volume_up","Volume +"),("mute","Mudo"),
                           ("previous","Anterior"),("play_pause","Play/Pause"),("next","Próxima")]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, a=key: self.act(a))
            media.addWidget(button)
        layout.addLayout(media)

        layout.addWidget(QLabel("Conexões do notebook — consultas locais e atalhos do sistema"))
        self.device_status = QLabel("Clique para consultar. Não enviamos dados à IA.")
        self.device_status.setWordWrap(True)
        layout.addWidget(self.device_status)
        inspect = QPushButton("Consultar bateria, rede, RAM e disco")
        inspect.clicked.connect(lambda: self.device_status.setText(overview()))
        layout.addWidget(inspect)
        for entries in (
            (("wifi_settings","Wi-Fi"),("bluetooth_settings","Bluetooth"),
             ("sound_settings","Áudio")),
            (("storage_settings","Armazenamento"),("clock_app","Alarmes"),
             ("calendar_settings","Data e agenda")),
        ):
            line = QHBoxLayout()
            for key, label in entries:
                button = QPushButton(label)
                button.clicked.connect(lambda checked=False,a=key:self.act(a))
                line.addWidget(button)
            layout.addLayout(line)
        more = QHBoxLayout()
        note_button = QPushButton("Notificações do Windows")
        note_button.clicked.connect(lambda: self.act("notifications_panel"))
        more.addWidget(note_button)
        clip_button = QPushButton("Ver texto copiado (agora)")
        clip_button.clicked.connect(self.inspect_clipboard)
        more.addWidget(clip_button)
        layout.addLayout(more)
        layout.addWidget(QLabel("Chrome — clique na extensão para compartilhar a aba atual"))
        token = QPushButton("Copiar código de conexão para a extensão")
        token.clicked.connect(lambda: QApplication.clipboard().setText(self.prefs["token"]))
        layout.addWidget(token)
        self.page_info = QLabel("Nenhuma página compartilhada nesta sessão")
        self.page_info.setWordWrap(True)
        layout.addWidget(self.page_info)
        self.page_text = QTextEdit()
        self.page_text.setReadOnly(True)
        self.page_text.setPlaceholderText("O texto autorizado da página aparece aqui; não é enviado à nuvem.")
        layout.addWidget(self.page_text, 1)
        self.home.chrome_bridge.received.connect(self.on_page)
        if self.home.last_page:
            self.on_page(*self.home.last_page)
        end = QPushButton("Concluir")
        end.clicked.connect(self.accept)
        layout.addWidget(end)

    def inspect_clipboard(self):
        # Qt clipboard is inspected ONLY from an explicit button click.
        text = QApplication.clipboard().text().strip()
        if not text:
            self.device_status.setText("Área de transferência sem texto.")
        else:
            self.device_status.setText("Texto copiado (prévia local): "+text[:700])

    def changed(self, key, value):
        self.prefs[key] = bool(value)
        save_preferences(self.prefs)

    def act(self, key):
        if not self.prefs.get("windows_controls"):
            self.action_status.setText("Ative os controles do Windows antes.")
            return
        try:
            execute_windows_action(key)
            self.action_status.setText("Ação executada: " + key)
        except Exception as exc:
            self.action_status.setText("Ação não executada: " + str(exc))

    def on_page(self,title,url,text):
        self.page_info.setText(f"{title}\n{url}")
        self.page_text.setPlainText(text)

    def closeEvent(self,event):
        try:
            self.home.chrome_bridge.received.disconnect(self.on_page)
        except (TypeError,RuntimeError):
            pass
        super().closeEvent(event)
