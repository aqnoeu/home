"""Compartilhamento do contrato de IA do Home (Windows e Android).

O serviço remoto é opcional, protegido por HTTPS e token de acesso próprio.
Nunca colocar uma chave de provedor de IA no cliente.
"""
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from PySide6.QtCore import QThread, Signal

CONFIG_PATH = Path.home() / ".home_ai.json"
DEFAULT_ENDPOINT = "https://home-ai.aqnoeu-home.workers.dev/ai"


def load_ai_settings():
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {"endpoint": str(data.get("endpoint", "")), "token": str(data.get("token", ""))}
    except (OSError, ValueError):
        pass
    return {"endpoint": DEFAULT_ENDPOINT, "token": ""}


def save_ai_settings(endpoint, token):
    endpoint, token = endpoint.strip(), token.strip()
    if endpoint:
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Use um endpoint HTTPS válido, sem credenciais na URL.")
    # Configuração local destinada ao token de acesso próprio do proxy Home,
    # nunca à chave principal de um provedor de IA.
    temporary = CONFIG_PATH.with_name(CONFIG_PATH.name + ".tmp")
    temporary.write_text(json.dumps({"endpoint": endpoint, "token": token}), encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(CONFIG_PATH)


def ask_home_ai(message, mood, endpoint, token):
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Endereço do servidor de IA inválido.")
    if not token:
        raise ValueError("Falta o código de acesso ao servidor do Home.")
    body = json.dumps({"message": message[:500], "mood": int(mood)}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "Home-Windows-AI"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read(12001)
    if len(raw) > 12000:
        raise ValueError("Resposta do servidor muito extensa.")
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Resposta inválida.")
    return (str(result.get("reply", "Sem resposta."))[:2000],
            max(0, min(3, int(result.get("mood", mood)))))


class AiWorker(QThread):
    replied = Signal(str, int)
    failed = Signal(str)

    def __init__(self, message, mood, endpoint, token, parent=None):
        super().__init__(parent)
        self.message = message
        self.mood = mood
        self.endpoint = endpoint
        self.token = token

    def run(self):
        try:
            answer, mood = ask_home_ai(self.message, self.mood, self.endpoint, self.token)
            self.replied.emit(answer, mood)
        except Exception as exc:
            self.failed.emit(str(exc)[:200])
