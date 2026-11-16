"""Windows adapter for the Android HOME Groq protocol.

The wire protocol and response decoding live in home_groq_client.py.
The only platform-specific concern here is the Windows Credential Manager.
"""
import urllib.request  # Kept importable for existing transport regression tests.
from PySide6.QtCore import QThread, Signal
from home_groq_client import (
    MODEL, FALLBACK_MODELS, SYSTEM, API,
    chat, list_models, explain_http_error,
)

SERVICE = "HOME-Groq"
ACCOUNT = "personal-api-key"


def get_key():
    try:
        import keyring
        value = keyring.get_password(SERVICE, ACCOUNT)
    except Exception:
        return None
    return value.strip() if isinstance(value, str) and value.strip().startswith("gsk_") else None


def has_native_key():
    """Public desktop builds never embed an API key."""
    return False


def save_key(value):
    normalized = (value or "").strip()
    if not normalized.startswith("gsk_") or len(normalized) < 25:
        raise ValueError("A chave Groq deve começar com gsk_.")
    import keyring
    keyring.set_password(SERVICE, ACCOUNT, normalized)
    retrieved = keyring.get_password(SERVICE, ACCOUNT)
    if retrieved != normalized:
        raise RuntimeError("A chave não pôde ser recuperada do cofre do Windows.")
    return True


def clear_key():
    import keyring
    try:
        keyring.delete_password(SERVICE, ACCOUNT)
    except keyring.errors.PasswordDeleteError:
        pass


def explain_groq_http_error(error):
    return explain_http_error(error)


def available_groq_models(api_key=None):
    key = api_key or get_key()
    return list_models(key)


def verify_groq_credentials(api_key=None):
    """A successful models request confirms authentication, not chat access."""
    available_groq_models(api_key)
    return True


def ask_groq(message, history=None, api_key=None, structured=False):
    key = api_key or get_key()
    speech, emotion = chat(key, message, history)
    return (speech, emotion) if structured else speech


class GroqWorker(QThread):
    answered = Signal(str)
    emotional_answer = Signal(str, str)
    credentials_checked = Signal(bool)
    failed = Signal(str)

    def __init__(self, question, history=None, parent=None, check_credentials=False):
        super().__init__(parent)
        self.question = question
        self.history = list(history or [])
        self.check_credentials = check_credentials

    def run(self):
        try:
            if self.check_credentials:
                verify_groq_credentials()
                self.credentials_checked.emit(True)
            speech, emotion = ask_groq(self.question, self.history, structured=True)
            self.emotional_answer.emit(speech, emotion)
            self.answered.emit(speech)
        except Exception as error:
            self.failed.emit(str(error)[:200])
