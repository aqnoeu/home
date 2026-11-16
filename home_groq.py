"""Private Groq conversational client for HOME Windows.

No proxy, server or key embedded in the application. Key is stored in the
Windows Credential Manager through keyring (never in a JSON config or GitHub).
The assistant's generated text is sent to the local Faber Piper speech engine.
"""
import json
import re
import urllib.error
import urllib.request
from home_emotions import normalize_emotion

from PySide6.QtCore import QThread, Signal

API = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"
FALLBACK_MODELS = ("llama-3.3-70b-versatile", "llama-3.1-8b-instant")
SERVICE = "HOME-Groq"
ACCOUNT = "personal-api-key"
SYSTEM = (
    "Você é HOME (Helpful, Organized, Mindful & Efficient), um assistente "
    "simpático, objetivo e discreto. Responda naturalmente em português brasileiro "
    "em até duas frases, preferencialmente com no máximo 380 caracteres. "
    "O texto será lido em voz alta: não use markdown, emojis ou listas. "
    "Não invente fatos. Você não executa ações do Windows. "
    "Retorne somente um objeto JSON com duas chaves: resposta (texto curto para falar) "
    "e emocao (neutro, raiva, sonolento ou tedio). Não use outras chaves."
)


def get_key():
    # Always prefer a key entered by the owner on this PC. Older packaged keys
    # must not override it (a common cause of HTTP 401 despite a valid user key).
    try:
        import keyring
        own = keyring.get_password(SERVICE, ACCOUNT)
        if own and own.strip().startswith("gsk_"):
            return own.strip()
    except Exception:
        # A failure reading the Windows vault must never silently select a
        # packaged key and cause misleading HTTP 401 responses.
        return None
    return None


def has_native_key():
    """Legacy compatibility: releases no longer bundle personal API keys."""
    return False


def save_key(value):
    value = (value or "").strip()
    if not value.startswith("gsk_") or len(value) < 25:
        raise ValueError("Chave Groq inválida. Copie a chave criada no painel Groq.")
    import keyring
    keyring.set_password(SERVICE, ACCOUNT, value)
    # Verify the exact key can be read back, rather than just trusting that
    # the credential manager accepted the write.
    recovered = keyring.get_password(SERVICE, ACCOUNT)
    if recovered is None or recovered.strip() != value:
        raise RuntimeError("A chave não pôde ser recuperada do Gerenciador de Credenciais do Windows.")
    return True


def clear_key():
    import keyring
    try:
        keyring.delete_password(SERVICE, ACCOUNT)
    except keyring.errors.PasswordDeleteError:
        pass


def explain_groq_http_error(exc):
    """Distinguish model/organization/project permissions without showing API secrets."""
    try:
        raw=exc.read(8193)
        if len(raw)>8192:
            return "Groq HTTP %s: retorno de erro muito grande." % exc.code
        payload=json.loads(raw)
        details=payload.get("error", {})
        if not isinstance(details, dict):
            details={}
        code=details.get("code","")
        kind=details.get("type","")
        remote_message=details.get("message","")
    except (OSError, ValueError, TypeError, AttributeError):
        code=kind=remote_message=""
    if exc.code == 401:
        return "Groq HTTP 401: credencial recusada. Troque a chave salva no HOME."
    if exc.code == 403:
        if code == "model_permission_blocked_org":
            return ("Groq HTTP 403: modelo bloqueado pela organização. "
                    "Verifique Organization → Limits na Groq.")
        if code == "model_permission_blocked_project":
            return ("Groq HTTP 403: modelo bloqueado pelo projeto. "
                    "Verifique Project → Limits na Groq.")
        if code:
            # The code is a classifier, not an arbitrary server message.
            safe_code="".join(ch for ch in str(code) if ch.isascii() and
                              (ch.isalnum() or ch in "_-"))[:70]
            return "Groq HTTP 403: permissão negada (código %s)." % safe_code
        # Preserve the provider's reason for otherwise opaque 403 responses.
        # Never reveal a secret from a server error message.
        if isinstance(remote_message, str) and remote_message.strip():
            safe = re.sub(r"gsk_[A-Za-z0-9_-]+", "[chave oculta]", remote_message)
            safe = re.sub(r"https?://\\S+", "[link]", safe)
            safe = " ".join(safe.split())[:160]
            if safe:
                return "Groq HTTP 403: " + safe
        if kind:
            safe_kind = "".join(ch for ch in str(kind) if ch.isascii() and
                                (ch.isalnum() or ch in "_-"))[:45]
            if safe_kind:
                return "Groq HTTP 403: acesso negado (tipo %s)." % safe_kind
        return ("Groq HTTP 403: acesso negado sem detalhes pela Groq. "
                "Confira permissões da organização e do projeto.")
    if exc.code == 429:
        return "Groq HTTP 429: limite de requisições atingido."
    if exc.code == 400:
        return ("Groq HTTP 400: parâmetros rejeitados pelo modelo. "
                "Verifique a versão do HOME.")
    return "Groq HTTP %s: solicitação não concluída." % exc.code


def available_groq_models(api_key=None):
    """Read available model identifiers using the locally saved credential."""
    key = api_key or get_key()
    if not key:
        raise RuntimeError("Nenhuma chave Groq recuperada do Windows.")
    request = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": "Bearer " + key, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(explain_groq_http_error(exc)) from None
    except urllib.error.URLError:
        raise RuntimeError("Não foi possível alcançar a Groq. Verifique rede e firewall.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("Resposta de modelos inesperada da Groq.")
    return {item["id"] for item in payload["data"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)}


def verify_groq_credentials(api_key=None):
    """A successful model listing proves authentication, not chat permission."""
    available_groq_models(api_key)
    return True


def _chat_request(key, model, messages):
    """Make one attempt; keep HTTP errors intact for precise retry decisions."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
        "max_completion_tokens": 500,
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    if model.startswith("openai/gpt-oss-"):
        payload.update({"reasoning_effort": "low", "include_reasoning": False})
    request = urllib.request.Request(
        API, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=28) as response:
        raw = response.read(128001)
    if len(raw) > 128000:
        raise RuntimeError("A resposta da Groq excedeu o limite.")
    try:
        answer = json.loads(raw)["choices"][0]["message"]["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("empty answer")
        decoded = json.loads(answer)
        speech = decoded["resposta"]
        if not isinstance(speech, str) or not speech.strip():
            raise ValueError("missing resposta")
        return speech.strip()[:850], normalize_emotion(decoded.get("emocao"))
    except (ValueError, TypeError, IndexError, KeyError, AttributeError):
        raise RuntimeError("A Groq não retornou JSON válido de resposta e emoção.") from None


def ask_groq(message, history=None, api_key=None, structured=False):
    key = api_key or get_key()
    if not key:
        raise RuntimeError("Nenhuma chave Groq recuperada do Gerenciador de Credenciais do Windows.")
    question = (message or "").strip()
    if not question or len(question) > 750:
        raise ValueError("Pergunta vazia ou maior que 750 caracteres.")
    messages = [{"role": "system", "content": SYSTEM}]
    for turn in (history or [])[-8:]:
        if (isinstance(turn, dict) and turn.get("role") in ("user", "assistant")
                and isinstance(turn.get("content"), str)):
            messages.append({"role": turn["role"], "content": turn["content"][:850]})
    messages.append({"role": "user", "content": question})

    # A 403 can mean model permissions, not an invalid API key.
    # Retry only well-known alternatives under the SAME local credential.
    rejected = []
    for model in (MODEL,) + FALLBACK_MODELS:
        try:
            speech, emotion = _chat_request(key, model, messages)
            return (speech, emotion) if structured else speech
        except urllib.error.HTTPError as exc:
            description = explain_groq_http_error(exc)
            if exc.code in (403, 404):
                rejected.append(model + ": " + description)
                continue
            raise RuntimeError(description) from None
        except urllib.error.URLError:
            raise RuntimeError("Não foi possível conectar à Groq. Verifique a internet.") from None
    raise RuntimeError(
        "Nenhum modelo autorizado para conversa. " +
        (rejected[-1] if rejected else "Groq recusou todas as tentativas.") +
        " Verifique Organization/Project → Limits."
    )


def diagnose_groq_chat(api_key=None):
    """Validate the REAL completion path; models listing alone is not enough."""
    available_groq_models(api_key)
    return ask_groq("Responda com um JSON contendo resposta igual a oi e emocao neutro.",
                    api_key=api_key, structured=True)


class GroqWorker(QThread):
    answered=Signal(str)
    emotional_answer=Signal(str,str)
    credentials_checked=Signal(bool)
    failed=Signal(str)

    def __init__(self, question, history=None, parent=None, check_credentials=False):
        super().__init__(parent)
        self.question=question
        self.history=list(history or [])
        self.check_credentials=check_credentials

    def run(self):
        try:
            if self.check_credentials:
                verify_groq_credentials()
                self.credentials_checked.emit(True)
            speech,emotion=ask_groq(self.question,self.history,structured=True)
            self.emotional_answer.emit(speech,emotion)
            self.answered.emit(speech)
        except Exception as exc:
            self.failed.emit(str(exc)[:200])
