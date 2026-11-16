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
    # Always prefer a key entered by the owner on this PC. Older packaged keys
    # must not override it (a common cause of HTTP 401 despite a valid user key).
    try:
        import keyring
        own = keyring.get_password(SERVICE, ACCOUNT)
        if own and own.strip().startswith("gsk_"):
            return own.strip()
    except Exception:
        pass
    return BUILTIN_GROQ_KEY.strip() if BUILTIN_GROQ_KEY.strip().startswith("gsk_") else None


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
    except (OSError, ValueError, TypeError, AttributeError):
        code=kind=""
    if exc.code == 401:
        return "Groq HTTP 401: credencial recusada. Troque a chave salva no HOME."
    if exc.code == 403:
        if code == "model_permission_blocked_org":
            return ("Groq HTTP 403: o modelo openai/gpt-oss-20b foi bloqueado "
                    "pela organização. Verifique Settings → Organization → Limits.")
        if code == "model_permission_blocked_project":
            return ("Groq HTTP 403: o modelo openai/gpt-oss-20b foi bloqueado "
                    "pelo projeto. Verifique Settings → Project → Limits.")
        if code:
            # The code is a classifier, not an arbitrary server message.
            safe_code="".join(ch for ch in str(code) if ch.isascii() and
                              (ch.isalnum() or ch in "_-"))[:70]
            return "Groq HTTP 403: permissão negada (código %s)." % safe_code
        return ("Groq HTTP 403: requisição proibida. A chave pode estar válida, "
                "mas o projeto, organização ou acesso ao modelo precisa ser verificado.")
    if exc.code == 429:
        return "Groq HTTP 429: limite de requisições atingido."
    if exc.code == 400:
        return ("Groq HTTP 400: parâmetros rejeitados pelo modelo. "
                "Verifique a versão do HOME.")
    return "Groq HTTP %s: solicitação não concluída." % exc.code


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
        raise RuntimeError(explain_groq_http_error(exc)) from None
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
