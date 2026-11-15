"""Integrações locais do Home: controles Windows e ponte de leitura opt-in do Chrome."""
import ctypes
import json
import secrets
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PySide6.QtCore import QObject, Signal
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
}
MEDIA_KEYS = {"volume_up": 0xAF, "volume_down": 0xAE, "mute": 0xAD,
              "play_pause": 0xB3, "next": 0xB0, "previous": 0xB1}


def load_preferences():
    base = {"eyes_follow_mouse": False, "eyes_react_clicks": False,
            "windows_controls": False, "chrome_reading": False, "token": secrets.token_urlsafe(32)}
    try:
        source = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for key in base:
            if key == "token" and isinstance(source.get(key), str) and len(source[key]) >= 32:
                base[key] = source[key]
            elif key != "token" and isinstance(source.get(key), bool):
                base[key] = source[key]
    except (OSError, ValueError, TypeError):
        pass
    return base


def save_preferences(prefs):
    CONFIG_PATH.write_text(json.dumps(prefs, indent=2), encoding="utf-8")


def execute_windows_action(action):
    if sys.platform != "win32":
        raise RuntimeError("Controles disponíveis somente no Windows.")
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
        self.setMinimumSize(475, 490)
        self.setStyleSheet("""
            QDialog {background:#171819;color:#ededed;}
            QLabel,QCheckBox {color:#dedede;}
            QPushButton {background:#292b2e;color:#eee;border:1px solid #454749;border-radius:9px;padding:9px;}
            QPushButton:hover {background:#383b3e;}
            QTextEdit {background:#202224;color:#dadada;border:1px solid #444;border-radius:8px;}
        """)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Permissões e interações do Home"))
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

    def changed(self, key, value):
        self.prefs[key] = bool(value)
        save_preferences(self.prefs)

    def act(self, key):
        if not self.prefs.get("windows_controls"):
            QMessageBox.information(self, "Permissão necessária", "Ative os controles do Windows antes.")
            return
        try:
            execute_windows_action(key)
        except Exception as exc:
            QMessageBox.warning(self, "Ação não executada", str(exc))

    def on_page(self,title,url,text):
        self.page_info.setText(f"{title}\n{url}")
        self.page_text.setPlainText(text)

    def closeEvent(self,event):
        try:
            self.home.chrome_bridge.received.disconnect(self.on_page)
        except (TypeError,RuntimeError):
            pass
        super().closeEvent(event)
