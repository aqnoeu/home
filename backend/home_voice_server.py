"""Servidor privado para a MESMA voz Alex (Kokoro pm_alex) do Home Windows.

Implantação em máquina Linux/Windows com Python, memória suficiente e HTTPS
terminado num proxy. Não publica a chave nem expõe a porta diretamente.
Exige HOME_TTS_INTERNAL_TOKEN e modelo Kokoro idêntico ao Windows.
"""
import hmac
import io
import os
from pathlib import Path
import wave
import numpy as np
from fastapi import FastAPI, HTTPException, Request, Response
from kokoro_onnx import Kokoro

app = FastAPI(title="Home Voice — Alex", docs_url=None, redoc_url=None, openapi_url=None)
model = None
EXPECTED = os.getenv("HOME_TTS_INTERNAL_TOKEN", "")
MODEL_DIR = Path(os.getenv("HOME_KOKORO_MODEL_DIR", "./models/kokoro-v1.0"))


@app.on_event("startup")
def load_model():
    global model
    if not EXPECTED or len(EXPECTED) < 32:
        raise RuntimeError("HOME_TTS_INTERNAL_TOKEN não configurado")
    model_path = MODEL_DIR / "kokoro-v1.0.onnx"
    voices_path = MODEL_DIR / "voices-v1.0.bin"
    if not (model_path.is_file() and voices_path.is_file()):
        raise RuntimeError("Arquivos originais Kokoro Alex ausentes")
    model = Kokoro(str(model_path), str(voices_path))


@app.post("/tts")
async def tts(request: Request):
    provided = request.headers.get("X-Home-TTS-Token", "")
    if not hmac.compare_digest(provided, EXPECTED):
        raise HTTPException(status_code=401, detail="Não autorizado")
    if int(request.headers.get("Content-Length", "0") or "0") > 4096:
        raise HTTPException(status_code=413, detail="Mensagem muito longa")
    data = await request.json()
    text = data.get("text", "")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 500:
        raise HTTPException(status_code=400, detail="Texto inválido")
    rate = data.get("rate", 165)
    if type(rate) is not int or not 90 <= rate <= 280:
        raise HTTPException(status_code=400, detail="Velocidade inválida")
    speed = max(0.7, min(1.3, 1 + (rate - 165) / 230.0))
    try:
        # Mesma voz e arquivo de estilo utilizados no Home do Windows.
        audio, sample_rate = model.create(text.strip(), voice="pm_alex",
                                          speed=speed, lang="pt-br")
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        samples = (np.clip(samples, -1, 1) * 32767).astype("<i2")
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(int(sample_rate))
            wav.writeframes(samples.tobytes())
        return Response(content=buffer.getvalue(), media_type="audio/wav",
                        headers={"Cache-Control": "no-store",
                                 "X-Home-Voice": "pm_alex"})
    except Exception:
        raise HTTPException(status_code=503, detail="Síntese Alex indisponível")


@app.get("/health")
def health():
    return {"status": "ready" if model is not None else "unavailable",
            "voice": "pm_alex"}
