"""Home Voice: reconhecimento local pt-BR, wake phrase opcional e fala offline.

O microfone só é aberto após consentimento explícito. Áudio não é salvo nem enviado.
"""
import hashlib
import json
import os
import queue
import re
import shutil
import tempfile
import threading
import time
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QMessageBox, QGroupBox
)

from home_integrations import execute_windows_action, save_preferences

MODEL_NAME = "vosk-model-small-pt-0.3"
MODEL_URL = "https://alphacephei.com/vosk/models/" + MODEL_NAME + ".zip"
MODEL_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Home" / "models" / MODEL_NAME
MAX_DOWNLOAD = 65 * 1024 * 1024
MODEL_SHA256 = '6e1ce909032e1afa7a88e68a3d628ecafff302bdf195befab308826c395e93b7'
SAMPLE_RATE = 16000

def model_is_complete(directory=MODEL_DIR):
    """Aceita os layouts Vosk legado (flat) e atual (am/conf/graph)."""
    root = Path(directory)
    old_files = ("final.mdl", "mfcc.conf", "Gr.fst", "HCLr.fst")
    new_files = ("am/final.mdl", "conf/model.conf", "conf/mfcc.conf",
                 "graph/Gr.fst", "graph/HCLr.fst")
    return (all((root / name).is_file() for name in old_files)
            or all((root / name).is_file() for name in new_files))



def normalize(sentence):
    return "".join(c for c in unicodedata.normalize("NFKD", sentence.casefold())
                   if not unicodedata.combining(c)).strip()


def interpret(sentence):
    """Somente comandos predeterminados, sem shell, scripts ou navegação."""
    s = normalize(sentence)
    open_verbs = ("abra ", "abre ", "abrir ", "inicie ", "iniciar ", "mostre ")
    request_to_open = s.startswith(open_verbs)
    if request_to_open and any(word in s for word in ("bloco de notas", "notepad")):
        return ("notepad", "Abrindo o Bloco de Notas.")
    if request_to_open and "calculadora" in s:
        return ("calc", "Abrindo a Calculadora.")
    if request_to_open and any(word in s for word in ("explorador", "arquivos")):
        return ("explorer", "Abrindo o Explorador de Arquivos.")
    if any(word in s for word in ("aumentar volume", "aumente o volume", "volume mais", "mais volume")):
        return ("volume_up", "Aumentando o volume.")
    if any(word in s for word in ("diminuir volume", "diminua o volume", "abaixar volume", "menos volume")):
        return ("volume_down", "Diminuindo o volume.")
    if any(word in s for word in ("silenciar", "sem som", "mudo")):
        return ("mute", "Alternando o som.")
    if any(word in s for word in ("pausar musica", "pausar midia", "continuar musica", "reproduzir musica", "play pause")):
        return ("play_pause", "Alternando a reprodução.")
    if "proxima musica" in s or "proxima faixa" in s:
        return ("next", "Próxima faixa.")
    if "musica anterior" in s or "faixa anterior" in s:
        return ("previous", "Faixa anterior.")
    return None


def wake_command(sentence):
    s = normalize(sentence)
    match = re.search(r"\b(?:ei|hey)[\s,]+(?:home|rome|romi)\b", s)
    return None if not match else s[match.end():].strip(" ,.!?")


class ModelDownloader(QThread):
    completed = Signal()
    failed = Signal(str)
    progress = Signal(str)

    def run(self):
        if model_is_complete():
            self.completed.emit()
            return
        parent = MODEL_DIR.parent
        parent.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix="home_voice_", dir=str(parent)))
        try:
            archive = temp_dir / "model.zip"
            req = urllib.request.Request(MODEL_URL, headers={"User-Agent": "Home-Voice/1.0"})
            digest = hashlib.sha256()
            with urllib.request.urlopen(req, timeout=45) as response, archive.open("wb") as out:
                if response.url != MODEL_URL:
                    raise RuntimeError("Endereço de download inesperado.")
                total = 0
                while True:
                    chunk = response.read(128 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD:
                        raise RuntimeError("Modelo excede o limite permitido.")
                    out.write(chunk)
                    digest.update(chunk)
                    if total % (5 * 1024 * 1024) < len(chunk):
                        self.progress.emit(f"Baixados {total // 1048576} MB...")
            if digest.hexdigest() != MODEL_SHA256:
                raise RuntimeError("Arquivo baixado não passou na verificação SHA-256. Tente novamente.")
            with zipfile.ZipFile(archive) as z:
                members = z.infolist()
                if sum(x.file_size for x in members) > 250 * 1024 * 1024:
                    raise RuntimeError("Modelo extraído excede o limite.")
                for item in members:
                    parts = Path(item.filename).parts
                    if not parts or parts[0] != MODEL_NAME or ".." in parts or item.is_dir():
                        continue
                    relative = Path(*parts[1:])
                    if not relative.parts:
                        continue
                    dst = temp_dir / "unpacked" / relative
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(item) as src, dst.open("wb") as dest:
                        shutil.copyfileobj(src, dest)
            unpacked = temp_dir / "unpacked"
            if not model_is_complete(unpacked):
                raise RuntimeError("Modelo de voz incompleto.")
            if MODEL_DIR.exists():
                shutil.rmtree(MODEL_DIR)
            shutil.move(str(unpacked), str(MODEL_DIR))
            self.completed.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class ListeningWorker(QThread):
    heard = Signal(str)
    mode_changed = Signal(str)
    error = Signal(str)

    def __init__(self, mode):
        super().__init__()
        self.mode = mode  # push ou wake
        self.stop_flag = threading.Event()

    def stop(self):
        self.stop_flag.set()

    def run(self):
        try:
            import sounddevice as sd
            from vosk import Model, KaldiRecognizer, SetLogLevel
            if not model_is_complete():
                raise RuntimeError("Instale primeiro o modelo de português.")
            SetLogLevel(-1)
            model = Model(str(MODEL_DIR))
            recognizer = KaldiRecognizer(model, SAMPLE_RATE)
            audio_q = queue.Queue(maxsize=20)
            def callback(indata, frames, time_info, status):
                try:
                    audio_q.put_nowait(bytes(indata))
                except queue.Full:
                    pass
            armed_until = 0.0
            start = time.monotonic()
            self.mode_changed.emit("Aguardando 'Ei, Home'..." if self.mode == "wake" else "Ouvindo...")
            with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4000, dtype="int16",
                                   channels=1, callback=callback):
                while not self.stop_flag.is_set():
                    if self.mode == "push" and time.monotonic() - start > 9:
                        final = json.loads(recognizer.FinalResult()).get("text", "").strip()
                        if final:
                            self.heard.emit(final)
                        else:
                            self.mode_changed.emit("Não detectei fala. Verifique o microfone padrão do Windows e tente novamente.")
                        return
                    try:
                        data = audio_q.get(timeout=0.15)
                    except queue.Empty:
                        continue
                    if not recognizer.AcceptWaveform(data):
                        continue
                    phrase = json.loads(recognizer.Result()).get("text", "").strip()
                    if not phrase:
                        continue
                    if self.mode == "push":
                        self.heard.emit(phrase)
                        return
                    inline = wake_command(phrase)
                    if inline is not None:
                        if inline:
                            self.heard.emit(inline)
                            return
                        armed_until = time.monotonic() + 7
                        self.mode_changed.emit("Estou ouvindo o comando...")
                    elif time.monotonic() < armed_until:
                        self.heard.emit(phrase)
                        return
                    else:
                        self.mode_changed.emit("Aguardando 'Ei, Home'...")
        except Exception as exc:
            self.error.emit(str(exc))


class SpeechWorker(QThread):
    done = Signal()
    failed = Signal(str)

    def __init__(self, message):
        super().__init__()
        self.message = message

    def run(self):
        try:
            import pyttsx3
            engine = pyttsx3.init(driverName="sapi5")
            for voice in engine.getProperty("voices"):
                info = (str(voice.id) + " " + str(voice.name) + " " + str(voice.languages)).lower()
                if any(value in info for value in ("pt-br", "pt_br", "portuguese", "brazil", "português")):
                    engine.setProperty("voice", voice.id)
                    break
            engine.setProperty("rate", 165)
            engine.say(self.message)
            engine.runAndWait()
            engine.stop()
        except Exception as exc:
            self.failed.emit(str(exc))
        self.done.emit()


class VoiceManager(QObject):
    state = Signal(str)
    command = Signal(str)

    def __init__(self, home):
        super().__init__(home)
        self.home = home
        self.prefs = home.integration_prefs
        self.worker = None
        self.speaker = None
        self.mode = None
        self.restart_wake = False
        self.dialog = None
        self.pending_push = False
        self.last_error = ""

    def set_state(self, state):
        self.state.emit(state)
        self.home.eyes.voice_state = state if state in ("listening", "thinking", "speaking") else ""
        self.home.eyes.update()

    def start(self, mode):
        if not self.prefs.get("voice_microphone"):
            self.set_state("Microfone desativado.")
            return
        if mode == "wake" and not self.prefs.get("voice_wake"):
            return
        if self.worker and self.worker.isRunning():
            return
        self.mode = mode
        self.last_error = ""
        self.restart_wake = mode == "wake"
        self.worker = ListeningWorker(mode)
        worker = self.worker
        worker.heard.connect(self.handle_heard)
        worker.error.connect(self.handle_error)
        worker.mode_changed.connect(self.set_state)
        worker.finished.connect(lambda: self.on_finished(worker))
        self.set_state("Preparando microfone...")
        worker.start()

    def on_finished(self, worker):
        if self.worker is worker:
            self.worker = None
        if self.pending_push:
            self.pending_push = False
            self.start('push')
            return
        if self.restart_wake and self.mode == "wake" and not self.speaker and self.prefs.get("voice_wake") and self.prefs.get("voice_microphone"):
            self.start("wake")
        elif not self.speaker and not self.last_error:
            self.set_state("Microfone pronto. Clique em Falar agora." if self.prefs.get("voice_microphone") else "Microfone desativado.")

    def stop(self):
        self.pending_push = False
        self.restart_wake = False
        self.mode = None
        if self.worker:
            self.worker.stop()
        self.set_state("Microfone pronto. Clique em Falar agora." if self.prefs.get("voice_microphone") else "Microfone desativado.")

    def toggle_push(self):
        if self.worker and self.worker.isRunning():
            if self.mode == 'wake':
                self.pending_push = True
                self.restart_wake = False
                self.worker.stop()
            else:
                self.stop()
        else:
            self.start("push")

    def refresh_permissions(self):
        if not self.prefs.get("voice_microphone") or not self.prefs.get("voice_wake"):
            self.stop()
        elif (not self.speaker or not self.speaker.isRunning()) and (not self.worker or not self.worker.isRunning()):
            self.start("wake")

    def handle_error(self, message):
        self.restart_wake = False
        self.mode = None
        self.last_error = "Falha no microfone: " + message[:220]
        self.set_state(self.last_error)

    def handle_heard(self, phrase):
        self.restart_wake = self.mode == "wake"
        self.mode = None
        self.set_state("thinking")
        self.command.emit(phrase)
        action = interpret(phrase)
        if action is None:
            self.speak("Não reconheci esse comando.")
            return
        key, response = action
        if not self.prefs.get("windows_controls"):
            self.speak("Ative os controles do Windows nas permissões.")
            return
        # Sempre solicitar consentimento específico antes de alterar programas/som.
        answer = QMessageBox.question(
            self.home, "Home — Confirmar comando de voz",
            f"Você disse: {phrase}\n\nAutoriza: {key}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            self.speak("Comando cancelado.")
            return
        try:
            execute_windows_action(key)
            self.speak(response)
        except Exception as exc:
            self.speak("Não consegui executar o comando.")
            self.set_state(str(exc)[:90])

    def speak(self, message):
        if not self.prefs.get("voice_speech"):
            self.set_state(message)
            if self.restart_wake and (not self.worker or not self.worker.isRunning()):
                self.mode = "wake"
                self.start("wake")
            elif self.restart_wake:
                self.mode = "wake"
            return
        self.set_state("speaking")
        self.speaker = SpeechWorker(message)
        speaker = self.speaker
        speaker.finished.connect(lambda: self.speech_finished(speaker))
        speaker.failed.connect(lambda error: self.state.emit("Voz indisponível: " + error[:90]))
        speaker.start()

    def speech_finished(self, speaker):
        if self.speaker is speaker:
            self.speaker = None
        if self.restart_wake and self.prefs.get("voice_wake") and self.prefs.get("voice_microphone"):
            self.mode = "wake"
            if not self.worker or not self.worker.isRunning():
                self.start("wake")
        else:
            self.set_state("")


class VoiceDialog(QDialog):
    def __init__(self, home):
        super().__init__(home)
        self.home = home
        self.manager = home.voice
        self.prefs = home.integration_prefs
        self.setWindowTitle("Home — Voz e microfone")
        self.setMinimumWidth(435)
        self.setStyleSheet("""
            QDialog{background:#18191b;color:#eee}
            QLabel,QCheckBox,QGroupBox{color:#e4e4e4}
            QGroupBox{border:1px solid #414246;border-radius:9px;margin-top:10px;padding:12px}
            QPushButton{background:#2d2f32;color:#eee;border:1px solid #505154;border-radius:9px;padding:9px}
            QPushButton:hover{background:#3b3d40}
        """)
        outer=QVBoxLayout(self)
        outer.addWidget(QLabel("Português • processamento local • sem gravação de áudio"))
        for key, text in [
            ("voice_microphone", "Permitir que o Home use o microfone"),
            ("voice_wake", 'Ativar escuta contínua de "Ei, Home"'),
            ("voice_speech", "Permitir respostas faladas"),
        ]:
            c=QCheckBox(text)
            c.setChecked(self.prefs.get(key, False))
            c.toggled.connect(lambda value, k=key: self.changed(k,value))
            outer.addWidget(c)
        self.model_btn=QPushButton("Baixar modelo de português (aprox. 31 MB)")
        self.model_btn.clicked.connect(self.download)
        outer.addWidget(self.model_btn)
        self.push_btn=QPushButton("🎙  Falar agora / parar")
        self.push_btn.clicked.connect(self.manager.toggle_push)
        outer.addWidget(self.push_btn)
        outer.addWidget(QLabel("Comandos: calculadora, bloco de notas, arquivos, volume e música."))
        self.state_label=QLabel(
            "Microfone pronto. Clique em Falar agora." if self.prefs.get("voice_microphone")
            else "Microfone desativado. Ative a permissão acima.")
        self.state_label.setWordWrap(True)
        outer.addWidget(self.state_label)
        self.manager.state.connect(self.state_label.setText)
        self.manager.command.connect(self.heard)
        self.finished.connect(self.disconnect_signals)
        self.download_worker=None
        if model_is_complete():
            self.model_btn.setText("✓ Modelo de português instalado")
        close=QPushButton("Concluir")
        close.clicked.connect(self.accept)
        outer.addWidget(close)

    def changed(self, key, value):
        self.prefs[key]=bool(value)
        save_preferences(self.prefs)
        self.manager.refresh_permissions()
        if key == "voice_microphone":
            self.state_label.setText(
                "Microfone pronto. Clique em Falar agora." if value
                else "Microfone desativado. Ative a permissão acima.")

    def download(self):
        if self.download_worker and self.download_worker.isRunning():
            return
        answer=QMessageBox.question(
            self,"Baixar modelo de voz",
            "Baixar o modelo português do site oficial Vosk?\n"
            "O download fica armazenado somente no seu computador.",
            QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.model_btn.setEnabled(False)
        self.download_worker=ModelDownloader(self)
        self.download_worker.progress.connect(self.model_btn.setText)
        self.download_worker.failed.connect(lambda err: self.model_btn.setText("Falha: "+err[:100]))
        self.download_worker.completed.connect(lambda: self.model_btn.setText("✓ Modelo de português instalado"))
        self.download_worker.completed.connect(self.manager.refresh_permissions)
        self.download_worker.finished.connect(lambda: self.model_btn.setEnabled(True))
        self.download_worker.start()

    def heard(self, text):
        self.state_label.setText("Reconhecido: " + text)

    def disconnect_signals(self,*args):
        try:
            self.manager.state.disconnect(self.state_label.setText)
            self.manager.command.disconnect(self.heard)
        except (RuntimeError,TypeError):
            pass
