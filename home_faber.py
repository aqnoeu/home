"""Faber pt_BR-faber-medium TTS shared by Home Windows and Android.

Both platforms download the same sherpa-onnx VITS Piper model archive.
The Windows runtime uses the sherpa_onnx Python package locally.
"""
import hashlib
import os
import shutil
import tarfile
import tempfile
import threading
import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Signal

MODEL_NAME = "vits-piper-pt_BR-faber-medium"
MODEL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/" + MODEL_NAME + ".tar.bz2"
MODEL_SHA256 = "7add3f923ad6bc25ca8a192805fd1a64d1b3893e4611c4a9719545a825039a83"
ARCHIVE_MAX = 90_000_000
EXTRACT_MAX = 130_000_000
MODEL_ROOT = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / "Home" / "models" / MODEL_NAME
PREVIEW_TEXT = "Olá! Eu sou o Home, com a voz Faber. Agora posso falar com você sem internet."
VOICE = "pt_BR-faber-medium"

# Load ONNX and the phonemizer only once per application process.
_ENGINE_LOCK = threading.Lock()
_ENGINE = None
_ENGINE_ROOT = None


def installed(root=MODEL_ROOT):
    root = Path(root)
    return (
        (root / "pt_BR-faber-medium.onnx").is_file()
        and (root / "pt_BR-faber-medium.onnx").stat().st_size > 40_000_000
        and (root / "tokens.txt").is_file()
        and (root / "tokens.txt").stat().st_size > 100
        and all((root / "espeak-ng-data" / name).is_file() for name in (
            "phontab", "phonindex", "phondata", "intonations"
        ))
    )


def synthesize(message, rate=165, root=MODEL_ROOT):
    if not installed(root):
        raise FileNotFoundError("Instale a voz Faber na página Voz.")
    global _ENGINE, _ENGINE_ROOT
    import sherpa_onnx
    root = Path(root)
    speed = max(0.8, min(1.25, 1.0 + (int(rate)-165)/250.0))
    with _ENGINE_LOCK:
        if _ENGINE is None or _ENGINE_ROOT != root:
            config = sherpa_onnx.OfflineTtsConfig(
                model=sherpa_onnx.OfflineTtsModelConfig(
                    vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                        model=str(root / "pt_BR-faber-medium.onnx"),
                        tokens=str(root / "tokens.txt"),
                        data_dir=str(root / "espeak-ng-data"),
                    ),
                    num_threads=2,
                    debug=False,
                )
            )
            if not config.validate():
                raise RuntimeError("Modelo Faber incompleto ou configuração inválida.")
            _ENGINE = sherpa_onnx.OfflineTts(config)
            _ENGINE_ROOT = root
        audio = _ENGINE.generate(message[:500], sid=0, speed=speed)
    if not len(audio.samples) or audio.sample_rate <= 0:
        raise RuntimeError("Faber produziu áudio vazio. Verifique o motor e os recursos do fonemizador.")
    return audio.samples, audio.sample_rate


class FaberDownloadWorker(QThread):
    progress = Signal(str)
    completed = Signal()
    failed = Signal(str)

    def run(self):
        if installed():
            self.completed.emit()
            return
        MODEL_ROOT.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".faber-", dir=MODEL_ROOT.parent))
        try:
            archive = temporary / "faber.tar.bz2"
            self.progress.emit("Baixando Faber (~67 MB)…")
            digest = hashlib.sha256()
            total = 0
            request = urllib.request.Request(MODEL_URL, headers={"User-Agent":"Home-Faber/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as output:
                if response.url.split(":",1)[0] != "https":
                    raise ValueError("Origem do modelo precisa ser HTTPS.")
                while True:
                    if self.isInterruptionRequested():
                        return
                    chunk = response.read(256*1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > ARCHIVE_MAX:
                        raise ValueError("Arquivo excede o limite.")
                    output.write(chunk)
                    digest.update(chunk)
                    if total % (8*1024*1024) < len(chunk):
                        self.progress.emit(f"Baixando Faber: {total//1048576} MB")
            if digest.hexdigest() != MODEL_SHA256:
                raise ValueError("Arquivo Faber não passou na verificação SHA-256.")
            dest = temporary / "model"
            dest.mkdir()
            extracted = 0
            self.progress.emit("Preparando voz Faber…")
            with tarfile.open(archive, "r:bz2") as tar:
                for member in tar:
                    if self.isInterruptionRequested():
                        return
                    if not member.isfile():
                        continue
                    parts = Path(member.name).parts
                    if not parts or ".." in parts:
                        continue
                    relative = Path(*parts[1:]) if parts[0] == MODEL_NAME else Path(*parts)
                    if not relative.parts:
                        continue
                    if relative.parts[0] != "espeak-ng-data" and str(relative) not in (
                        "pt_BR-faber-medium.onnx", "tokens.txt"
                    ):
                        continue
                    extracted += member.size
                    if extracted > EXTRACT_MAX:
                        raise ValueError("Modelo extraído excede o limite.")
                    target = dest / relative
                    if not target.resolve().is_relative_to(dest.resolve()):
                        raise ValueError("Caminho do modelo inválido.")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source = tar.extractfile(member)
                    if source is None:
                        continue
                    with source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
            if not installed(dest):
                raise ValueError("Pacote Faber sem modelo, tokens ou espeak-ng-data.")
            if MODEL_ROOT.exists():
                shutil.rmtree(MODEL_ROOT)
            shutil.move(str(dest), str(MODEL_ROOT))
            self.completed.emit()
        except Exception as exc:
            self.failed.emit(str(exc)[:240])
        finally:
            shutil.rmtree(temporary, ignore_errors=True)


class FaberSpeechWorker(QThread):
    failed = Signal(str)

    def __init__(self, message, rate=165, volume=100):
        super().__init__()
        self.message = message
        self.rate = rate
        self.volume = volume

    def run(self):
        try:
            import numpy as np
            import sounddevice as sd
            samples, sample_rate = synthesize(self.message, rate=self.rate)
            adjusted = np.clip(np.asarray(samples, dtype=np.float32) *
                               (max(0,min(100,self.volume))/100.0),-1,1)
            sd.play(adjusted, sample_rate, blocking=True)
        except Exception as exc:
            self.failed.emit("Faber: " + str(exc)[:200])
