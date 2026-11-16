"""Private Groq conversational client for HOME Windows.

No proxy, server or key embedded in the application. Key is stored in the
Windows Credential Manager through keyring (never in a JSON config or GitHub).
The assistant's generated text is sent to the local Faber Piper speech engine.
"""
import json
import urllib.error
import urllib.request
from home_groq_builtin import BUILTIN_GROQ_KEY
from home_emotions import normalize_emotion

from PySide6.QtCore import QThread, Signal

API = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"
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
    if BUILTIN_GROQ_KEY.startswith("gsk_"):
        return BUILTIN_GROQ_KEY
    try:
        import keyring
        return keyring.get_password(SERVICE, ACCOUNT)
    except Exception:
        return None


def has_native_key():
    return BUILTIN_GROQ_KEY.startswith("gsk_")


def save_key(value):
    value = (value or "").strip()
    if not value.startswith("gsk_") or len(value) < 25:
        raise ValueError("Chave Groq inválida. Copie a chave criada no painel Groq.")
    import keyring
    keyring.set_password(SERVICE, ACCOUNT, value)


def clear_key():
    import keyring
    try:
        keyring.delete_password(SERVICE, ACCOUNT)
    except keyring.errors.PasswordDeleteError:
        pass


def ask_groq(message, history=None, api_key=None, structured=False):
    key = api_key or get_key()
    if not key:
        raise RuntimeError("A Groq ainda não foi provisionada nesta compilação do HOME.")
    question = (message or "").strip()
    if not question or len(question) > 750:
        raise ValueError("Pergunta vazia ou maior que 750 caracteres.")
    messages = [{"role":"system", "content":SYSTEM}]
    for turn in (history or [])[-8:]:
        if turn.get("role") in ("user", "assistant") and isinstance(turn.get("content"), str):
            messages.append({"role":turn["role"], "content":turn["content"][:850]})
    messages.append({"role":"user","content":question})
    request=urllib.request.Request(
        API,
        data=json.dumps({
            "model":MODEL,
            "messages":messages,
            "temperature":0.5,
            "max_completion_tokens":450,
            "reasoning_effort":"low",
            "include_reasoning":False,
            "response_format":{"type":"json_object"},
            "stream":False
        },ensure_ascii=False).encode("utf-8"),
        headers={"Authorization":"Bearer "+key, "Content-Type":"application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request,timeout=28) as response:
            raw=response.read(128001)
            if len(raw)>128000:
                raise RuntimeError("Resposta da Groq excedeu o limite.")
    except urllib.error.HTTPError as exc:
        if exc.code in (401,403):
            raise RuntimeError("Chave Groq recusada. Verifique em Conectar Groq.") from None
        if exc.code==429:
            raise RuntimeError("Limite da Groq atingido. Tente mais tarde.") from None
        raise RuntimeError("Groq indisponível (HTTP %s)." % exc.code) from None
    except urllib.error.URLError:
        raise RuntimeError("Não foi possível conectar à Groq. Verifique a internet.") from None
    try:
        answer=json.loads(raw)["choices"][0]["message"]["content"].strip()
    except (ValueError, TypeError, IndexError, KeyError, AttributeError):
        raise RuntimeError("A Groq retornou uma resposta inválida.") from None
    if not answer:
        raise RuntimeError("A Groq não enviou texto para responder.")
    try:
        decoded=json.loads(answer)
        speech=decoded["resposta"]
        if not isinstance(speech,str) or not speech.strip():
            raise ValueError("resposta vazia")
        emotion=normalize_emotion(decoded.get("emocao"))
    except (ValueError,TypeError,KeyError):
        raise RuntimeError("A Groq não retornou JSON de resposta e emoção.") from None
    return (speech.strip()[:850], emotion) if structured else speech.strip()[:850]


class GroqWorker(QThread):
    answered=Signal(str)
    emotional_answer=Signal(str,str)
    failed=Signal(str)

    def __init__(self, question, history=None, parent=None):
        super().__init__(parent)
        self.question=question
        self.history=list(history or [])

    def run(self):
        try:
            speech,emotion=ask_groq(self.question,self.history,structured=True)
            self.emotional_answer.emit(speech,emotion)
            self.answered.emit(speech)
        except Exception as exc:
            self.failed.emit(str(exc)[:200])
