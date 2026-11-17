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

from PySide6.QtCore import QThread, Signal, QObject, Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QMessageBox, QGroupBox, QWidget, QComboBox, QSlider
)

from home_integrations import execute_windows_action, save_preferences
import home_voice_profile
from home_device import local_query
from home_faber import FaberDownloadWorker, FaberSpeechWorker, installed as faber_installed, PREVIEW_TEXT
from home_groq import GroqWorker, get_key

MODEL_NAME = "vosk-model-small-pt-0.3"
MODEL_URL = "https://alphacephei.com/vosk/models/" + MODEL_NAME + ".zip"
MODEL_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Home" / "models" / MODEL_NAME
MAX_DOWNLOAD = 65 * 1024 * 1024
MODEL_SHA256 = '6e1ce909032e1afa7a88e68a3d628ecafff302bdf195befab308826c395e93b7'
SAMPLE_RATE = 16000

_MODEL = None
_MODEL_LOCK = threading.Lock()


def load_model():
    """Carrega o modelo Vosk uma única vez; recarregar a cada turno deixava o Home surdo por segundos."""
    global _MODEL
    from vosk import Model
    with _MODEL_LOCK:
        if _MODEL is None:
            _MODEL = Model(str(MODEL_DIR))
        return _MODEL


def reset_model_cache():
    global _MODEL
    with _MODEL_LOCK:
        _MODEL = None


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


FILLER_WORDS = {
    "por", "favor", "pode", "poderia", "consegue", "quero", "queria", "gostaria",
    "vamos", "agora", "entao", "eu", "me", "home", "ok", "ei", "hey", "voce",
    "da", "de", "um", "uma", "ai", "so", "la",
}
OPEN_VERBS = {"abra", "abre", "abrir", "abri", "inicie", "iniciar", "mostre", "mostrar", "execute"}
VOLUME_UP = ("aument", "suba", "sobe", "subir", "eleve", "elevar", "mais alto", "mais volume", "volume mais")
VOLUME_DOWN = ("diminu", "abaix", "reduz", "baixa", "baixe", "baixar", "menos volume", "volume menos", "mais baixo")


def _command_text(sentence):
    """Normaliza e remove palavras de cortesia do início ("por favor, pode abrir...")."""
    words = re.findall(r"[a-z0-9\-]+", normalize(sentence))
    while words and words[0] in FILLER_WORDS and (len(words) > 1):
        if words[0] in OPEN_VERBS:
            break
        words.pop(0)
    return " ".join(words)


def interpret(sentence):
    """Somente comandos predeterminados, sem shell, scripts ou navegação."""
    s = _command_text(sentence)
    first = s.split(" ", 1)[0] if s else ""
    request_to_open = first in OPEN_VERBS
    if request_to_open and any(word in s for word in ("bloco de notas", "bloco de nota", "notepad")):
        return ("notepad", "Abrindo o Bloco de Notas.")
    if request_to_open and "calculadora" in s:
        return ("calc", "Abrindo a Calculadora.")
    if request_to_open and any(word in s for word in ("explorador", "arquivos")):
        return ("explorer", "Abrindo o Explorador de Arquivos.")
    if request_to_open and any(word in s for word in ("gerenciador de tarefas", "task manager")):
        return ("taskmgr", "Abrindo o Gerenciador de Tarefas.")
    if request_to_open and any(word in s for word in ("painel de controle", "control panel")):
        return ("control_panel", "Abrindo o Painel de Controle.")
    panels = (
        ("bluetooth", "bluetooth_settings", "Abrindo ajustes de Bluetooth."),
        ("wi-fi", "wifi_settings", "Abrindo ajustes de Wi-Fi."),
        ("wifi", "wifi_settings", "Abrindo ajustes de Wi-Fi."),
        ("configuracoes de som", "sound_settings", "Abrindo ajustes de som."),
        ("alarme", "clock_app", "Abrindo o aplicativo de relógio."),
        ("relogio", "clock_app", "Abrindo o aplicativo de relógio."),
        ("armazenamento", "storage_settings", "Abrindo o armazenamento."),
        ("calendario", "calendar_settings", "Abrindo ajustes de data."),
        ("notificacoes", "notifications_panel", "Abrindo notificações do Windows."),
    )
    if request_to_open:
        for term, action_key, reply in panels:
            if term in s:
                return (action_key, reply)
    if "volume" in s:
        if any(word in s for word in VOLUME_UP):
            return ("volume_up", "Aumentando o volume.")
        if any(word in s for word in VOLUME_DOWN):
            return ("volume_down", "Diminuindo o volume.")
    if any(word in s for word in ("silenciar", "silencie", "mutar", "sem som", "mudo")):
        return ("mute", "Alternando o som.")
    if any(word in s for word in ("pausar musica", "pausar midia", "pausar a musica", "continuar musica",
                                  "continuar a musica", "reproduzir musica", "play pause")):
        return ("play_pause", "Alternando a reprodução.")
    if "proxima musica" in s or "proxima faixa" in s or "pular musica" in s:
        return ("next", "Próxima faixa.")
    if "musica anterior" in s or "faixa anterior" in s:
        return ("previous", "Faixa anterior.")
    return None


# O modelo Vosk pt-BR não conhece "home" nem "ok": costuma transcrever como
# "rome", "homem", "oquei", "o k"... Aceitamos essas variantes, mas só no INÍCIO da frase.
CALL_WORDS = {"ei", "hey", "hei", "ey", "oi", "ae", "ai", "oque", "ok", "okay", "okey", "oke", "okei", "oquei", "oquey", "okê"}
HOME_WORDS = {"home", "homi", "homy", "hom", "ome", "homem", "rome", "romi", "romy", "rhome", "rhomi",
              "rom", "roume", "roumi", "roumy", "houmi", "houme", "hôme"}
JOINED_WAKE = {c + h for c in CALL_WORDS for h in HOME_WORDS}  # "okhome", "eiromi"...
BARE_WAKE = {"home", "rome", "romi", "romy", "rhome", "rhomi", "roume", "roumi", "roumy", "houmi", "houme"}


def wake_command(sentence):
    """Se a frase começa com a chamada ("ok Home", "ei Home"), devolve o comando
    que vem depois (pode ser ""). Caso contrário, None."""
    words = re.findall(r"[a-z0-9]+", normalize(sentence))
    # Aceita apenas um "e" inicial isolado, evitando ativar no meio de conversas.
    offsets = (0, 1) if words and words[0] == "e" else (0,)
    for i in offsets:
        rest = None
        w = words[i:]
        if w and w[0] in JOINED_WAKE:
            rest = w[1:]
        elif len(w) >= 2 and w[0] in CALL_WORDS and w[1] in HOME_WORDS:
            rest = w[2:]
        elif len(w) >= 3 and w[0] == "o" and w[1] in ("k", "que", "key") and w[2] in HOME_WORDS:
            rest = w[3:]
        elif i == 0 and w and w[0] in BARE_WAKE:
            rest = w[1:]
        if rest is not None:
            return " ".join(rest).strip()
    return home_voice_profile.wake_suffix(sentence)


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
            reset_model_cache()
            self.completed.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class ListeningWorker(QThread):
    heard = Signal(str)
    wake_heard = Signal()
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
            from vosk import KaldiRecognizer, SetLogLevel
            if not model_is_complete():
                raise RuntimeError("Instale primeiro o modelo de português.")
            SetLogLevel(-1)
            model = load_model()
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
                        self.wake_heard.emit()
                        if inline:
                            self.heard.emit(inline)
                            return
                        armed_until = time.monotonic() + 10
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
    wake_detected = Signal()
    chat_updated = Signal()

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
        self.faber_download_worker = None
        self.ai_worker = None

    def _resume_wake_after_turn(self):
        """Match Android: pause listening while answering, resume after audio or failure."""
        if not (self.restart_wake and self.prefs.get("voice_wake")
                and self.prefs.get("voice_microphone")):
            return
        if self.ai_worker is not None or (self.speaker and self.speaker.isRunning()):
            return
        def resume():
            if not (self.restart_wake and self.prefs.get("voice_wake")
                    and self.prefs.get("voice_microphone")):
                return
            if not self.worker or not self.worker.isRunning():
                self.start("wake")
        QTimer.singleShot(650, resume)

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
        worker.wake_heard.connect(self.wake_detected)
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
        if self.ai_worker and self.ai_worker.isRunning():
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
            local = local_query(phrase)
            if local is not None:
                self.home.record_chat("user",phrase)
                self.home.record_chat("home",local)
                self.chat_updated.emit()
                self.speak(local)
                return
            if not get_key():
                notice = "Conecte a Groq uma vez no Assistente para receber respostas por voz."
                self.home.record_chat("user", phrase)
                self.home.record_chat("home", notice)
                self.chat_updated.emit()
                self.set_state(notice)
                self._resume_wake_after_turn()
                return
            if self.ai_worker and self.ai_worker.isRunning():
                self.set_state("O Home ainda está pensando na pergunta anterior.")
                return
            # Only model-generated text is spoken. No AI instruction can execute OS actions.
            chat_id=self.home.chat_store.active()
            history=self.home.chat_store.context(chat_id)
            self.home.record_chat("user",phrase,session=chat_id)
            self.chat_updated.emit()
            self.ai_worker = GroqWorker(phrase,history,parent=self.home)
            self.ai_worker.chat_id=chat_id
            ai=self.ai_worker
            ai.emotional_answer.connect(lambda _text, emotion:self.home.set_ai_emotion(emotion))
            ai.answered.connect(lambda response:self.on_ai_reply(ai,response))
            ai.failed.connect(lambda problem:self.on_ai_error(ai,problem))
            self.set_state("Groq está pensando…")
            ai.start()
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

    def on_ai_reply(self, worker, response):
        if self.ai_worker is not worker:
            return
        self.ai_worker = None
        self.home.record_chat("home",response,session=worker.chat_id)
        self.chat_updated.emit()
        self.speak(response, force=True)

    def on_ai_error(self, worker, problem):
        if self.ai_worker is not worker:
            return
        self.ai_worker = None
        message = "Falha na Groq: " + problem[:150]
        self.home.record_chat("home", message, session=worker.chat_id)
        self.chat_updated.emit()
        self.set_state(message)
        self._resume_wake_after_turn()

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
            self._resume_wake_after_turn()
            return
        if not faber_installed():
            self.set_state("Faber não instalada. Abra Voz e instale o modelo local gratuito.")
            self._resume_wake_after_turn()
            return
        self.set_state("speaking")
        self.speaker = FaberSpeechWorker(
            message, self.prefs.get("voice_rate",165),
            self.prefs.get("voice_volume",100))
        speaker = self.speaker
        speaker.finished.connect(lambda: self.speech_finished(speaker))
        speaker.failed.connect(lambda error: self.state.emit("Falha ao falar: "+error[:160]))
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
        self._resume_wake_after_turn()



class VoiceEnrollmentDialog(QDialog):
    """Training uses independent on-demand captures; never opens a second continuous mic."""
    def __init__(self, home):
        super().__init__(home)
        self.home = home
        self.worker = None
        self.last_heard = ""
        self.setWindowTitle("HOME — Cadastro de voz")
        self.setMinimumWidth(390)
        self.setStyleSheet("QDialog{background:#0B111A;color:white}QLabel,QCheckBox{color:#FFFFFF}QPushButton{background:#223957;color:white;padding:10px;border-radius:8px}")
        layout = QVBoxLayout(self)
        self.title = QLabel("")
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.detail = QLabel("O cadastro é local. Correções de texto não treinam biometria vocal.")
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)
        self.allow = QCheckBox("Aprendizado por correções ativado")
        self.allow.setChecked(home_voice_profile.load()["corrections"])
        self.allow.toggled.connect(self.toggle_corrections)
        layout.addWidget(self.allow)
        self.listen = QPushButton("Gravar e conferir frase")
        self.listen.clicked.connect(self.record)
        layout.addWidget(self.listen)
        self.correct = QPushButton("Eu disse a frase solicitada — registrar correção")
        self.correct.clicked.connect(self.confirm_correction)
        self.correct.hide()
        layout.addWidget(self.correct)
        self.repeat = QPushButton("Repetir teste")
        self.repeat.clicked.connect(self.repeat_test)
        self.repeat.hide()
        layout.addWidget(self.repeat)
        reset = QPushButton("Apagar cadastro e reiniciar")
        reset.clicked.connect(self.reset_profile)
        layout.addWidget(reset)
        self.refresh()
    def toggle_corrections(self, enabled):
        data=home_voice_profile.load()
        data["corrections"]=enabled
        home_voice_profile.save(data)
    def refresh(self):
        step=home_voice_profile.load()["step"]
        self.correct.hide()
        self.repeat.hide()
        self.listen.setEnabled(step<len(home_voice_profile.PROMPTS))
        if step==len(home_voice_profile.PROMPTS):
            self.title.setText("✓ Seis testes concluídos")
            self.detail.setText("As variantes confirmadas ficam neste Windows. Nenhum áudio foi enviado.")
        else:
            kind="chamada isolada" if step<3 else "chamada + função"
            self.title.setText(f"Teste {step+1} de 6 — {kind}\nDiga: {home_voice_profile.PROMPTS[step]}")
            self.detail.setText("Teste a frase naturalmente e confira o texto reconhecido.")
    def record(self):
        if self.worker and self.worker.isRunning():return
        if not model_is_complete():
            self.detail.setText("Instale primeiro o modelo de português Vosk na página Voz.")
            return
        if not self.home.integration_prefs.get("voice_microphone"):
            self.detail.setText("Ative a permissão de microfone na página Voz.")
            return
        if self.home.voice.worker and self.home.voice.worker.isRunning():
            self.detail.setText("Pare a escuta contínua antes de cadastrar a voz, evitando dois microfones.")
            return
        self.listen.setEnabled(False)
        self.detail.setText("Ouvindo a frase do teste...")
        self.worker=ListeningWorker("push")
        self.worker.heard.connect(self.heard)
        self.worker.error.connect(lambda e:self.detail.setText("Falha de captura: "+e))
        self.worker.finished.connect(lambda:self.listen.setEnabled(True))
        self.worker.start()
    def heard(self, phrase):
        step=home_voice_profile.load()["step"]
        if step>=len(home_voice_profile.PROMPTS):return
        self.last_heard=phrase
        if home_voice_profile.matches(step,phrase):
            home_voice_profile.accept(phrase)
            self.refresh()
            self.detail.setText("✓ Reconhecido: "+phrase+("\nFunção reconhecida no teste; execução não solicitada." if step>=3 else ""))
        else:
            self.detail.setText("O Windows entendeu: "+phrase+"\nVocê disse: "+home_voice_profile.PROMPTS[step]+"?")
            self.correct.setVisible(self.allow.isChecked())
            self.repeat.show()
    def confirm_correction(self):
        if not self.allow.isChecked() or not self.last_heard:return
        home_voice_profile.accept(self.last_heard, corrected=True)
        self.refresh()
        self.detail.setText("Correção registrada localmente. A variante textual poderá ser aceita.")
    def repeat_test(self):
        self.last_heard=""
        self.refresh()
    def reset_profile(self):
        home_voice_profile.reset()
        self.allow.setChecked(True)
        self.refresh()

class VoiceDialog(QDialog):
    def __init__(self, home):
        super().__init__(home)
        self.home = home
        self.manager = home.voice
        self.prefs = home.integration_prefs
        self.setWindowTitle("Home — Voz e microfone")
        self.setMinimumWidth(395)
        self.setStyleSheet("""
            QDialog{background:#0B111A;color:#eee}
            QLabel,QCheckBox,QGroupBox{color:#FFFFFF}
            QGroupBox{border:1px solid #324357;border-radius:9px;margin-top:10px;padding:12px}
            QPushButton{background:#1C2737;color:#eee;border:1px solid #324357;border-radius:9px;padding:9px}
            QPushButton:hover{background:#26384F}
        """)
        outer=QVBoxLayout(self)
        outer.setContentsMargins(16,18,16,14)
        outer.setSpacing(10)
        outer.addWidget(QLabel("Faber • voz offline, sem servidor de áudio"))
        for key, text in [
            ("voice_speech", "Permitir respostas faladas com Faber"),
            ("voice_microphone", "Permitir que o Home use o microfone"),
            ("voice_wake", 'Ativar escuta contínua de "Ei, Home"'),
        ]:
            c=QCheckBox(text)
            c.setChecked(self.prefs.get(key, False))
            c.toggled.connect(lambda value, k=key: self.changed(k,value))
            outer.addWidget(c)
        outer.addWidget(QLabel("Voz Faber • Português brasileiro • gratuita e offline"))
        self.faber_info = QLabel("")
        self.faber_info.setWordWrap(True)
        outer.addWidget(self.faber_info)
        self.faber_button=QPushButton("Instalar Faber (~67 MB)")
        self.faber_button.clicked.connect(self.download_faber)
        outer.addWidget(self.faber_button)
        self.refresh_faber()
        self.rate_slider=QSlider(Qt.Horizontal)
        self.rate_slider.setRange(90,280)
        self.rate_slider.setValue(int(self.prefs.get("voice_rate",165)))
        self.rate_slider.valueChanged.connect(self.change_rate)
        outer.addWidget(QLabel("Velocidade da fala"))
        outer.addWidget(self.rate_slider)
        self.volume_slider=QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0,100)
        self.volume_slider.setValue(int(self.prefs.get("voice_volume",100)))
        self.volume_slider.valueChanged.connect(self.change_volume)
        outer.addWidget(QLabel("Volume"))
        outer.addWidget(self.volume_slider)
        self.preview_button=QPushButton("▶ Testar Faber offline")
        self.preview_button.clicked.connect(self.preview_faber)
        outer.addWidget(self.preview_button)
        self.model_btn=QPushButton("Baixar modelo de português (aprox. 31 MB)")
        self.model_btn.clicked.connect(self.download)
        outer.addWidget(self.model_btn)
        self.push_btn=QPushButton("🎙  Falar agora / parar")
        self.push_btn.clicked.connect(self.manager.toggle_push)
        outer.addWidget(self.push_btn)
        self.enroll_btn=QPushButton("Cadastrar minha voz — chamadas e funções")
        self.enroll_btn.clicked.connect(lambda:VoiceEnrollmentDialog(self.home).exec())
        outer.addWidget(self.enroll_btn)
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

    def refresh_faber(self):
        installed = faber_installed()
        self.faber_button.setText("✓ Faber instalada" if installed else "↓ Instalar Faber (~67 MB)")
        self.faber_button.setEnabled(not installed)
        self.faber_info.setText("Pronta para uso offline." if installed
                                else "Download inicial de aproximadamente 67 MB. Sem chave, servidor ou assinatura.")

    def download_faber(self):
        if self.manager.faber_download_worker and self.manager.faber_download_worker.isRunning():
            return
        self.faber_button.setEnabled(False)
        worker=FaberDownloadWorker(self.manager)
        self.manager.faber_download_worker=worker
        worker.progress.connect(self.faber_info.setText)
        worker.completed.connect(self.refresh_faber)
        worker.failed.connect(lambda message:self.faber_info.setText("Falha na instalação: "+message))
        worker.finished.connect(self.refresh_faber)
        worker.start()

    def preview_faber(self):
        if not faber_installed():
            self.faber_info.setText("Instale Faber antes de testar.")
            return
        self.manager.speak(PREVIEW_TEXT,force=True)

    def change_rate(self,value):
        self.prefs["voice_rate"]=int(value)
        save_preferences(self.prefs)

    def change_volume(self,value):
        self.prefs["voice_volume"]=int(value)
        save_preferences(self.prefs)

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
