"""Desktop port of Android HomeGroq's HTTPS chat contract.

Uses the same endpoint, system roles, JSON response format and timeouts as
android/app/src/main/java/com/aqnoeu/home/HomeGroq.java.
Transport is stdlib urllib because Android HttpURLConnection is unavailable on Windows.
No credentials are embedded, logged or persisted by this module.
"""
import json
import re
import urllib.error
import urllib.request

API = "https://api.groq.com/openai/v1/chat/completions"
MODELS_API = "https://api.groq.com/openai/v1/models"
MODEL = "openai/gpt-oss-20b"
FALLBACK_MODELS = ("openai/gpt-oss-120b", "qwen/qwen3.8-27b")
SYSTEM = (
    "Você é HOME. Fale naturalmente em português brasileiro, de forma breve, "
    "sem markdown ou emojis. Não invente fatos ou execute ações. "
    "Responda estritamente em JSON com duas chaves: resposta (texto curto) "
    "e emocao (neutro, raiva, sonolento, tedio, piscadela, lovabow, "
    "pensando, surpreso, desconfiado, timido, confuso, travesso)."
)
EMOTIONS = {
    "neutro", "raiva", "sonolento", "tedio",
    "piscadela", "lovabow", "pensando", "surpreso",
    "desconfiado", "timido", "confuso", "travesso",
}


def explain_http_error(error):
    """Preserve the provider's code and safe reason without exposing a secret."""
    status = error.code
    try:
        payload = json.loads(error.read(8192))
        info = payload.get("error", {}) if isinstance(payload, dict) else {}
        if not isinstance(info, dict):
            info = {}
    except (ValueError, OSError, TypeError, AttributeError):
        info = {}
    code = info.get("code", "")
    message = info.get("message", "")
    if status == 401:
        return "Groq HTTP 401: a chave não foi autenticada."
    if status == 429:
        return "Groq HTTP 429: limite de utilização atingido."
    if status == 403 and code == "model_permission_blocked_project":
        return "Groq HTTP 403: modelo bloqueado pelo projeto. Verifique Project → Limits."
    if status == 403 and code == "model_permission_blocked_org":
        return "Groq HTTP 403: modelo bloqueado pela organização. Verifique Organization → Limits."
    prefix = "Groq HTTP %s" % status
    if isinstance(code, str) and code:
        clean_code = re.sub("[^A-Za-z0-9_-]", "", code)[:70]
        if clean_code:
            return prefix + ": " + clean_code
    if isinstance(message, str) and message:
        cleaned = re.sub(r"gsk_[A-Za-z0-9_-]+", "[credencial oculta]", message)
        cleaned = re.sub(r"https?://\S+", "[endereço omitido]", cleaned)
        cleaned = " ".join(cleaned.split())[:160]
        if cleaned:
            return prefix + ": " + cleaned
    if status == 403:
        return prefix + ": acesso negado pelo provedor ou pela rede; verifique o projeto e o modelo."
    return prefix + ": requisição recusada."


def list_models(key):
    if not key:
        raise RuntimeError("Conecte a chave Groq nas configurações.")
    request = urllib.request.Request(
        MODELS_API, headers={
            "Authorization": "Bearer " + key,
            "Accept": "application/json",
        }, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(explain_http_error(error)) from None
    except urllib.error.URLError:
        raise RuntimeError("Não foi possível conectar à Groq. Verifique rede ou proxy.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("Resposta inesperada da Groq ao consultar os modelos.")
    return {entry.get("id") for entry in payload["data"]
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)}


def build_messages(question, history=None):
    text = (question or "").strip()
    if not text or len(text) > 750:
        raise ValueError("Pergunta vazia ou com mais de 750 caracteres.")
    result = [{"role": "system", "content": SYSTEM}]
    for entry in (history or [])[-8:]:
        if (isinstance(entry, dict) and entry.get("role") in ("user", "assistant")
                and isinstance(entry.get("content"), str)):
            result.append({
                "role": entry["role"], "content": entry["content"][:850]
            })
    result.append({"role": "user", "content": text})
    return result


def _attempt(key, model, messages):
    # Mirrors the Android client: structured JSON and a short speech answer.
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.5,
        "max_completion_tokens": 450,
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    if model.startswith("openai/gpt-oss-"):
        payload["reasoning_effort"] = "low"
        payload["include_reasoning"] = False
    request = urllib.request.Request(
        API,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=28) as response:
        raw = response.read(128001)
    if len(raw) > 128000:
        raise RuntimeError("Resposta da Groq excedeu o limite permitido.")
    try:
        answer = json.loads(raw)["choices"][0]["message"]["content"]
        structured = json.loads(answer)
        spoken = structured["resposta"]
        if not isinstance(spoken, str) or not spoken.strip():
            raise ValueError("empty response")
        emotion = structured.get("emocao", "neutro")
        return spoken.strip()[:850], emotion if emotion in EMOTIONS else "neutro"
    except (ValueError, TypeError, IndexError, KeyError, AttributeError):
        raise RuntimeError("A Groq não retornou JSON válido com resposta e emoção.") from None


def chat(key, question, history=None):
    if not key or not key.startswith("gsk_"):
        raise RuntimeError("Nenhuma chave Groq válida foi recuperada neste PC.")
    messages = build_messages(question, history)
    blocked = []
    for model in (MODEL,) + FALLBACK_MODELS:
        try:
            return _attempt(key, model, messages)
        except urllib.error.HTTPError as error:
            code = error.code
            reason = explain_http_error(error)
            # Never retry an authentication failure, rate-limit or invalid request.
            if code not in (403, 404):
                raise RuntimeError(reason) from None
            blocked.append(model + ": " + reason)
        except urllib.error.URLError:
            raise RuntimeError("Não foi possível conectar à Groq. Verifique rede ou proxy.") from None
    raise RuntimeError("A Groq recusou todos os modelos testados. " +
                       (blocked[-1] if blocked else "Verifique as permissões do projeto."))
