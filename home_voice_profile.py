"""Local HOME voice enrollment shared concept for Windows and Android.

Text corrections are not a biometric voiceprint. Raw audio never leaves the machine.
"""
import json
import re
import unicodedata
from pathlib import Path
from datetime import datetime

PROFILE = Path.home() / ".home_voice_profile.json"
PROMPTS = (
    "Ei Home", "Ok Home", "Home",
    "Ei Home, que horas são?",
    "Ok Home, que dia é hoje?",
    "Home, qual a bateria do computador?",
)

def normalize(text):
    s = unicodedata.normalize("NFD", (text or "").casefold())
    return re.sub(r"\\s+", " ", re.sub(r"[^a-z0-9 ]", " ", "".join(x for x in s if not unicodedata.combining(x)))).strip()

def load():
    try:
        d = json.loads(PROFILE.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return {"step": max(0, min(len(PROMPTS), int(d.get("step", 0)))),
                    "corrections": bool(d.get("corrections", True)),
                    "samples": list(d.get("samples", []))[-30:],
                    "aliases": list(d.get("aliases", []))[:15]}
    except (OSError, ValueError, TypeError):
        pass
    return {"step": 0, "corrections": True, "samples": [], "aliases": []}

def save(data):
    PROFILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def matches(step, heard):
    q = normalize(heard)
    wake = ("ei home", "ok home", "home")[step % 3]
    if step < 3:
        return q == wake or (wake == "ei home" and q == "hey home")
    if not (q.startswith(wake + " ") or (wake == "ei home" and q.startswith("hey home "))):
        return False
    if step == 3: return "hora" in q
    if step == 4: return "dia" in q and "hoje" in q
    return "bateria" in q or "carga" in q

def accept(heard, corrected=False):
    data = load()
    step = data["step"]
    if step >= len(PROMPTS): return
    data["samples"].append({"step": step, "expected": PROMPTS[step],
                            "heard": heard, "corrected": bool(corrected),
                            "date": datetime.now().isoformat(timespec="seconds")})
    data["samples"] = data["samples"][-30:]
    if corrected and data["corrections"] and step < 3:
        alias = normalize(heard)
        if 5 <= len(alias) <= 28 and len(alias.split()) <= 3 and alias != "home":
            if alias not in data["aliases"] and len(data["aliases"]) < 15:
                data["aliases"].append(alias)
    data["step"] = step + 1
    save(data)

def wake_suffix(phrase):
    """Only match reviewed aliases at the start of a complete recognition result."""
    data = load()
    if not data["corrections"]: return None
    text = normalize(phrase)
    for candidate in data["aliases"]:
        prefix = normalize(candidate)
        if len(prefix) < 5: continue
        if text == prefix: return ""
        if text.startswith(prefix + " "): return text[len(prefix):].strip()
    return None

def reset():
    try: PROFILE.unlink()
    except FileNotFoundError: pass
