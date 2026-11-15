"""Síntese neural local Kokoro (pt-BR), independente da plataforma Windows.

Arquivos do modelo só são baixados após ação explícita do usuário. O
motor recebe texto e devolve amostras: o aplicativo escolhe como reproduzi-las.
"""
import os
import tempfile
import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Signal

VOICE = "pm_alex"
MODEL_ROOT = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".local" / "share")) / "Home" / "models" / "kokoro-v1.0"
MODEL_URLS = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",
}
# Limites conservadores para rejeitar conteúdos incompletos / downloads inesperados.
MIN_SIZES = {"kokoro-v1.0.onnx": 100_000_000, "voices-v1.0.bin": 500_000}
MAX_SIZES = {"kokoro-v1.0.onnx": 500_000_000, "voices-v1.0.bin": 50_000_000}
PREVIEW_TEXT = "Olá! Eu sou o Home. Esta é a voz Alex, em português brasileiro."


def installed(root=MODEL_ROOT):
    root = Path(root)
    return all(
        (root / name).is_file()
        and MIN_SIZES[name] <= (root / name).stat().st_size <= MAX_SIZES[name]
        for name in MODEL_URLS
    )


def speed_from_rate(rate):
    """Mapeia a escala SAPI antiga (90–280) para a escala Kokoro (0.7–1.3)."""
    return max(0.7, min(1.3, 1.0 + (int(rate) - 165) / 230.0))


def synthesize(text, root=MODEL_ROOT, voice=VOICE, rate=165):
    """Gera (numpy.ndarray, sample_rate); não requer microfone nem Windows."""
    if not installed(root):
        raise FileNotFoundError("Instale a voz Alex antes de usá-la.")
    from kokoro_onnx import Kokoro
    engine = Kokoro(str(Path(root) / "kokoro-v1.0.onnx"),
                    str(Path(root) / "voices-v1.0.bin"))
    try:
        return engine.create(text, voice=voice, speed=speed_from_rate(rate), lang="pt-br")
    finally:
        voices = getattr(engine, "voices", None)
        if callable(getattr(voices, "close", None)):
            voices.close()


class KokoroDownloadWorker(QThread):
    progress = Signal(str)
    completed = Signal()
    failed = Signal(str)

    def run(self):
        if installed():
            self.completed.emit()
            return
        try:
            MODEL_ROOT.mkdir(parents=True, exist_ok=True)
            for name, url in MODEL_URLS.items():
                dest = MODEL_ROOT / name
                if dest.is_file() and MIN_SIZES[name] <= dest.stat().st_size <= MAX_SIZES[name]:
                    continue
                self.progress.emit("Baixando " + name + " (primeira instalação)...")
                fd, temporary = tempfile.mkstemp(prefix=".kokoro-", suffix=".part", dir=MODEL_ROOT)
                try:
                    with os.fdopen(fd, "wb") as output:
                        req = urllib.request.Request(url, headers={"User-Agent": "Home-Kokoro/1.0"})
                        with urllib.request.urlopen(req, timeout=60) as response:
                            # A CDN do GitHub redireciona via HTTPS.
                            if not response.url.startswith("https://"):
                                raise RuntimeError("Origem do modelo não utiliza HTTPS.")
                            total = 0
                            while True:
                                chunk = response.read(512 * 1024)
                                if not chunk:
                                    break
                                total += len(chunk)
                                if total > MAX_SIZES[name]:
                                    raise RuntimeError("Arquivo maior que o tamanho esperado.")
                                output.write(chunk)
                                if total % (20 * 1024 * 1024) < len(chunk):
                                    self.progress.emit(f"Baixando {name}: {total // 1048576} MB")
                    if total < MIN_SIZES[name]:
                        raise RuntimeError("Download incompleto: " + name)
                    os.replace(temporary, dest)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            if not installed():
                raise RuntimeError("Arquivos da voz Alex incompletos.")
            self.completed.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class KokoroSpeechWorker(QThread):
    failed = Signal(str)

    def __init__(self, message, rate=165, volume=100):
        super().__init__()
        self.message = str(message)
        self.rate = rate
        self.volume = volume

    def run(self):
        try:
            import numpy as np
            import sounddevice as sd
            audio, sample_rate = synthesize(self.message, rate=self.rate)
            data = np.asarray(audio, dtype=np.float32)
            data = np.clip(data * (max(0, min(100, int(self.volume))) / 100.0), -1, 1)
            sd.play(data, sample_rate, blocking=True)
        except Exception as exc:
            self.failed.emit("Kokoro Alex: " + str(exc)[:180])
