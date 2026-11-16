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

from PySide6.QtCore import QThread, Signal, QObject, Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QMessageBox, QGroupBox, QWidget, QComboBox, QSlider
)

from home_integrations import execute_windows_action, save_preferences
from home_kokoro import KokoroDownloadWorker, KokoroSpeechWorker, installed as kokoro_installed, PREVIEW_TEXT

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


class VoicesWorker(QThread):
    """Enumeração SAPI5 fora da interface; inicialização COM por thread."""
    loaded = Signal(object)
    failed = Signal(str)

    def run(self):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            import pyttsx3
            engine = pyttsx3.init(driverName="sapi5")
            voices = [
                (str(v.id), str(v.name), str(v.languages))
                for v in engine.getProperty("voices")
            ]
            engine.stop()
            self.loaded.emit(voices)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            pythoncom.CoUninitialize()


def preferred_voice(voices, selected_id=""):
    """Retorna o ID salvo se existir; do contrário, prefere português."""
    available = [(str(v.id), str(v.name), str(v.languages)) for v in voices]
    if selected_id and any(voice_id == selected_id for voice_id, _, _ in available):
        return selected_id
    for voice_id, name, language in available:
        info = (voice_id + " " + name + " " + language).casefold()
        if any(x in info for x in ("pt-br", "pt_br", "portuguese", "brazil", "português", "pt-pt")):
            return voice_id
    return None


class SpeechWorker(QThread):
    done = Signal()
    failed = Signal(str)

    def __init__(self, message, voice_id="", rate=165, volume=100):
        super().__init__()
        self.message = message
        self.voice_id = voice_id
        self.rate = max(90, min(280, int(rate)))
        self.volume = max(0, min(100, int(volume)))

    def run(self):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            import pyttsx3
            engine = pyttsx3.init(driverName="sapi5")
            voice_id = preferred_voice(engine.getProperty("voices"), self.voice_id)
            if voice_id:
                engine.setProperty("voice", voice_id)
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume / 100.0)
            engine.say(self.message)
            engine.runAndWait()
            engine.stop()
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            pythoncom.CoUninitialize()
            self.done.emit()


class VoiceManager(QObject):
    state = Signal(str)
    command = Signal(str)
    confirmation_requested = Signal(str, str)

    def __init__(self, home):
        super().__init__(home)
        self.home = home
        self.prefs = home.integration_prefs
        self.worker = None
        self.speaker = None
        self.speech_queue = []
        self.mode = None
        self.restart_wake = False
        self.dialog = None
        self.pending_push = False
        self.last_error = ""
        self.pending_action = None
        self.pending_phrase = ""
        self.download_worker = None
        self.voice_list_workers = []
        self.kokoro_download_worker = None

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
            from home_ai import AiWorker, load_ai_settings
            config = load_ai_settings()
            if config.get("endpoint") and config.get("token"):
                if not hasattr(self.home, "_ai_workers"):
                    self.home._ai_workers = []
                worker = AiWorker(phrase, self.home.eyes.mood,
                                  config["endpoint"], config["token"], self.home)
                self.home._ai_workers.append(worker)
                worker.replied.connect(lambda answer, mood: self.speak(answer))
                worker.failed.connect(lambda error: self.speak("Não consegui consultar a IA: " + error[:100]))
                worker.finished.connect(lambda w=worker: self.home._ai_workers.remove(w) if w in self.home._ai_workers else None)
                worker.start()
                return
            self.speak("Não reconheci esse comando. Configure a IA no Assistente para conversar.")
            return
        key, response = action
        if not self.prefs.get("windows_controls"):
            self.speak("Ative os controles do Windows nas permissões.")
            return
        # A confirmação aparece dentro da página Voz, nunca em um popup.
        self.pending_action = (key, response)
        self.pending_phrase = phrase
        # A espera por confirmação não deve manter os olhos em "pensando".
        self.set_state("Confirmação pendente.")
        self.confirmation_requested.emit(phrase, key)

    def decide_pending(self, approved):
        pending = self.pending_action
        self.pending_action = None
        self.pending_phrase = ""
        if not pending:
            return
        if not approved:
            self.speak("Comando cancelado.")
            return
        key, response = pending
        if not self.prefs.get("windows_controls"):
            self.speak("Permissão do Windows desativada.")
            return
        try:
            execute_windows_action(key)
            self.speak(response)
        except Exception:
            self.speak("Não consegui executar o comando.")

    def speak(self, message, force=False):
        if self.speaker and self.speaker.isRunning():
            self.speech_queue.append(message)
            self.speech_queue = self.speech_queue[-5:]
            return
        if not force and not self.prefs.get("voice_speech"):
            self.set_state(message)
            if self.restart_wake and (not self.worker or not self.worker.isRunning()):
                self.mode = "wake"
                self.start("wake")
            elif self.restart_wake:
                self.mode = "wake"
            return
        self.set_state("speaking")
        if self.prefs.get("voice_engine") == "kokoro" and kokoro_installed():
            self.speaker = KokoroSpeechWorker(
                message, self.prefs.get("voice_rate", 165),
                self.prefs.get("voice_volume", 100))
        else:
            self.speaker = SpeechWorker(
                message, self.prefs.get("voice_id", ""),
                self.prefs.get("voice_rate", 165), self.prefs.get("voice_volume", 100))
            if self.prefs.get("voice_engine") == "kokoro":
                self.state.emit("Alex ainda não instalada; usando voz do Windows temporariamente.")
        speaker = self.speaker
        speaker.finished.connect(lambda: self.speech_finished(speaker))
        speaker.failed.connect(lambda error: self.state.emit("Voz indisponível: " + error[:90]))
        speaker.start()

    def speech_finished(self, speaker):
        if self.speaker is speaker:
            self.speaker = None
        if self.speech_queue:
            next_message = self.speech_queue.pop(0)
            self.speak(next_message, force=True)
            return
        # Sempre encerrar visualmente a fala antes de tentar reativar o microfone.
        # start("wake") pode sair cedo se o worker anterior ainda estiver ativo.
        self.set_state("")
        if self.restart_wake and self.prefs.get("voice_wake") and self.prefs.get("voice_microphone"):
            self.mode = "wake"
            if not self.worker or not self.worker.isRunning():
                self.start("wake")



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
        # Motor de voz independente do reconhecimento/microfone.
        outer.addWidget(QLabel("Mecanismo de fala"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("Alex — Kokoro (pt-BR, neural e offline)", "kokoro")
        self.engine_combo.addItem("Vozes do Windows (SAPI5)", "sapi5")
        self.engine_combo.setCurrentIndex(
            max(0, self.engine_combo.findData(self.prefs.get("voice_engine", "kokoro"))))
        self.engine_combo.currentIndexChanged.connect(self.change_engine)
        outer.addWidget(self.engine_combo)
        self.kokoro_button = QPushButton("")
        self.kokoro_button.clicked.connect(self.download_kokoro)
        outer.addWidget(self.kokoro_button)
        self.kokoro_label = QLabel(
            "Alex usa modelo local Kokoro-82M (licença Apache 2.0). "
            "A transferência inicial é grande (~330 MB) e exige internet; depois funciona offline. "
            "Até instalar, as respostas usam temporariamente uma voz do Windows.")
        self.kokoro_label.setWordWrap(True)
        self.kokoro_label.setStyleSheet("color:#acadb0;font-size:11px")
        outer.addWidget(self.kokoro_label)
        self.refresh_kokoro()
        outer.addWidget(QLabel("Voz alternativa • Windows SAPI5"))
        self.voice_combo = QComboBox()
        self.voice_combo.setStyleSheet(
            "QComboBox{background:#2d2f32;color:#eee;border:1px solid #505154;"
            "border-radius:8px;padding:8px}"
            "QComboBox QAbstractItemView{background:#292b2e;color:#eee}")
        self.voice_combo.addItem("Carregando vozes do Windows...", "")
        self.voice_combo.setEnabled(False)
        self.voice_combo.currentIndexChanged.connect(self.select_voice)
        outer.addWidget(self.voice_combo)
        reload_button = QPushButton("↻ Atualizar lista de vozes")
        reload_button.clicked.connect(self.load_voices)
        outer.addWidget(reload_button)
        outer.addWidget(QLabel("Velocidade da fala"))
        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setRange(90, 280)
        self.rate_slider.setValue(int(self.prefs.get("voice_rate", 165)))
        self.rate_label = QLabel(str(self.rate_slider.value()))
        self.rate_slider.valueChanged.connect(self.change_rate)
        rate_row = QHBoxLayout()
        rate_row.addWidget(self.rate_slider, 1)
        rate_row.addWidget(self.rate_label)
        outer.addLayout(rate_row)
        outer.addWidget(QLabel("Volume da voz"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.prefs.get("voice_volume", 100)))
        self.volume_label = QLabel(str(self.volume_slider.value()) + "%")
        self.volume_slider.valueChanged.connect(self.change_volume)
        volume_row = QHBoxLayout()
        volume_row.addWidget(self.volume_slider, 1)
        volume_row.addWidget(self.volume_label)
        outer.addLayout(volume_row)
        self.preview_button = QPushButton("▶ Testar voz selecionada")
        self.preview_button.clicked.connect(self.preview_voice)
        outer.addWidget(self.preview_button)
        self.voice_info = QLabel("As vozes SAPI5 variam conforme a instalação do Windows.")
        self.voice_info.setWordWrap(True)
        outer.addWidget(self.voice_info)
        self.voices_worker = None
        self.load_voices()
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
        self.manager.confirmation_requested.connect(self.show_confirmation)
        self.finished.connect(self.disconnect_signals)
        self.confirm = QWidget()
        confirmation_layout = QVBoxLayout(self.confirm)
        self.confirm_label = QLabel("")
        self.confirm_label.setWordWrap(True)
        confirmation_layout.addWidget(self.confirm_label)
        buttons = QHBoxLayout()
        self.yes_btn = QPushButton("Sim, executar")
        self.yes_btn.clicked.connect(lambda:self.confirm_action(True))
        self.no_btn = QPushButton("Não, cancelar")
        self.no_btn.clicked.connect(lambda:self.confirm_action(False))
        buttons.addWidget(self.yes_btn)
        buttons.addWidget(self.no_btn)
        confirmation_layout.addLayout(buttons)
        self.confirm.hide()
        outer.addWidget(self.confirm)
        if self.manager.pending_action:
            self.show_confirmation(self.manager.pending_phrase, self.manager.pending_action[0])
        self.download_worker=None
        if model_is_complete():
            self.model_btn.setText("✓ Modelo de português instalado")
        close=QPushButton("Concluir")
        close.clicked.connect(self.accept)
        outer.addWidget(close)

    def refresh_kokoro(self):
        ready = kokoro_installed()
        self.kokoro_button.setText(
            "✓ Alex instalada — disponível offline" if ready
            else "⬇ Instalar Alex (Kokoro, ~330 MB)")
        self.kokoro_button.setEnabled(not ready)

    def change_engine(self, index):
        if index < 0:
            return
        engine = self.engine_combo.itemData(index)
        if engine not in ("kokoro", "sapi5"):
            return
        self.prefs["voice_engine"] = engine
        save_preferences(self.prefs)
        self.kokoro_label.setText(
            "Alex selecionada. " + ("Modelo instalado; pronto para testar." if kokoro_installed()
            else "Clique em Instalar Alex. Até lá, a voz do Windows será usada.")
            if engine == "kokoro" else
            "Motor Windows SAPI5 selecionado. O Home continua funcionando sem o Kokoro.")

    def download_kokoro(self):
        if self.manager.kokoro_download_worker and self.manager.kokoro_download_worker.isRunning():
            return
        if kokoro_installed():
            self.refresh_kokoro()
            return
        self.kokoro_button.setEnabled(False)
        self.kokoro_button.setText("Preparando download...")
        worker = KokoroDownloadWorker(self.manager)
        self.manager.kokoro_download_worker = worker
        worker.progress.connect(self.kokoro_button.setText)
        worker.completed.connect(self.kokoro_ready)
        worker.failed.connect(self.kokoro_error)
        worker.finished.connect(self.refresh_kokoro)
        worker.start()

    def kokoro_ready(self):
        self.refresh_kokoro()
        self.kokoro_label.setText("Alex instalada! Clique em Testar voz selecionada.")

    def kokoro_error(self, message):
        self.refresh_kokoro()
        self.kokoro_label.setText("Falha ao instalar Alex: " + message[:180])

    def load_voices(self):
        if self.voices_worker and self.voices_worker.isRunning():
            return
        self.voice_info.setText("Procurando vozes compatíveis no Windows...")
        self.voice_combo.setEnabled(False)
        self.voices_worker = VoicesWorker(self.manager)
        worker = self.voices_worker
        self.manager.voice_list_workers.append(worker)
        worker.finished.connect(lambda: self.manager.voice_list_workers.remove(worker)
                                if worker in self.manager.voice_list_workers else None)
        worker.loaded.connect(self.show_voices)
        worker.failed.connect(self.voice_error)
        worker.start()

    def show_voices(self, voices):
        selected = self.prefs.get("voice_id", "")
        self.voice_combo.blockSignals(True)
        self.voice_combo.clear()
        self.voice_combo.addItem("Automática (preferir português)", "")
        for voice_id, name, languages in voices:
            self.voice_combo.addItem(f"{name}  ·  {languages}", voice_id)
        idx = self.voice_combo.findData(selected)
        self.voice_combo.setCurrentIndex(max(0, idx))
        self.voice_combo.blockSignals(False)
        self.voice_combo.setEnabled(True)
        self.voice_info.setText(
            f"{len(voices)} voz(es) SAPI5 encontrada(s). A seleção é salva automaticamente."
            if voices else "Nenhuma voz SAPI5 encontrada. Verifique as vozes instaladas no Windows.")

    def voice_error(self, error):
        self.voice_combo.clear()
        self.voice_combo.addItem("Vozes indisponíveis", "")
        self.voice_info.setText("Não foi possível consultar as vozes do Windows: " + error[:160])

    def select_voice(self, index):
        if index < 0:
            return
        self.prefs["voice_id"] = str(self.voice_combo.itemData(index) or "")
        save_preferences(self.prefs)

    def change_rate(self, value):
        self.prefs["voice_rate"] = int(value)
        self.rate_label.setText(str(value))
        save_preferences(self.prefs)

    def change_volume(self, value):
        self.prefs["voice_volume"] = int(value)
        self.volume_label.setText(str(value) + "%")
        save_preferences(self.prefs)

    def preview_voice(self):
        if self.prefs.get("voice_engine") == "kokoro" and not kokoro_installed():
            self.kokoro_label.setText("Instale a voz Alex primeiro, usando o botão acima.")
            return
        self.voice_info.setText("Reproduzindo exemplo com a voz escolhida...")
        self.manager.speak(
            PREVIEW_TEXT if self.prefs.get("voice_engine") == "kokoro"
            else "Olá! Eu sou o Home. Esta é uma demonstração da voz selecionada.",
            force=True)

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
        self.model_btn.setEnabled(False)
        self.download_worker=ModelDownloader(self.manager)
        self.manager.download_worker=self.download_worker
        self.download_worker.progress.connect(self.model_btn.setText)
        self.download_worker.failed.connect(lambda err: self.model_btn.setText("Falha: "+err[:100]))
        self.download_worker.completed.connect(lambda: self.model_btn.setText("✓ Modelo de português instalado"))
        self.download_worker.completed.connect(self.manager.refresh_permissions)
        self.download_worker.finished.connect(lambda: self.model_btn.setEnabled(True))
        self.download_worker.start()

    def show_confirmation(self, phrase, action):
        self.confirm_label.setText(f"Você disse: {phrase}\n\nAutoriza a ação: {action}?")
        self.confirm.show()

    def confirm_action(self, approved):
        self.confirm.hide()
        self.manager.decide_pending(approved)

    def heard(self, text):
        self.state_label.setText("Reconhecido: " + text)

    def disconnect_signals(self,*args):
        try:
            self.manager.state.disconnect(self.state_label.setText)
            self.manager.command.disconnect(self.heard)
            self.manager.confirmation_requested.disconnect(self.show_confirmation)
        except (RuntimeError,TypeError):
            pass
