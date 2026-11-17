"""HOME Focus: timer local original, inspired by general productivity workflows.

No network, telemetry or OS command execution. The timer is scoped to the HOME
process, remains active when navigating between internal screens, and does not
pretend to run after the user fully closes HOME.
"""
import re
import time
import unicodedata

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QSpinBox


def _normalize(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c))


def parse_timer_command(text):
    """Return duration in seconds for explicitly requested local timers."""
    normalized = _normalize(text)
    if re.search(r"\b(modo foco|iniciar foco|comece foco|pomodoro)\b", normalized):
        return 25 * 60
    if not re.search(r"\b(temporizador|timer|cronometro regressivo)\b", normalized):
        return None
    match = re.search(r"\b(\d{1,3})\s*(minutos?|mins?|segundos?|segs?|horas?)\b", normalized)
    if not match:
        return None
    number = int(match.group(1))
    unit = match.group(2)
    seconds = number * (3600 if unit.startswith("hora") else
                        1 if unit.startswith(("seg",)) else 60)
    return seconds if 1 <= seconds <= 3*3600 else None


class FocusClock(QObject):
    changed = Signal()
    finished = Signal()

    def __init__(self):
        super().__init__()
        self.deadline = None
        self.remaining = 0
        self.active = False
        self.clock = QTimer(self)
        self.clock.setInterval(500)
        self.clock.timeout.connect(self.tick)

    def start(self, seconds):
        if not 1 <= seconds <= 10800:
            raise ValueError("Duração fora do limite de três horas.")
        self.remaining = seconds
        self.deadline = time.monotonic() + seconds
        self.active = True
        self.clock.start()
        self.changed.emit()

    def tick(self):
        if not self.active:
            return
        self.remaining = max(0, int(self.deadline - time.monotonic() + .999))
        self.changed.emit()
        if self.remaining == 0:
            self.active = False
            self.deadline = None
            self.clock.stop()
            self.finished.emit()

    def pause(self):
        if self.active:
            self.tick()
            if self.active:
                self.active = False
                self.clock.stop()
                self.changed.emit()

    def resume(self):
        if not self.active and self.remaining > 0:
            self.deadline = time.monotonic() + self.remaining
            self.active = True
            self.clock.start()
            self.changed.emit()

    def reset(self):
        self.active = False
        self.deadline = None
        self.remaining = 0
        self.clock.stop()
        self.changed.emit()


FOCUS = FocusClock()


class FocusPage(QWidget):
    """Compact concentration screen inside HOME's existing notch."""
    def __init__(self, home, parent=None):
        super().__init__(parent)
        self.home = home
        self.setStyleSheet("""
            QLabel {color:#DDE7F4}
            QPushButton {background:#1C2737;color:white;border:1px solid #324357;
                         border-radius:10px;padding:11px}
            QPushButton:hover {background:#26384F}
            QSpinBox {background:#1C2737;color:white;border:1px solid #324357;
                      border-radius:10px;padding:8px}
        """)
        layout = QVBoxLayout(self)
        intro = QLabel("Modo Foco · Temporizador offline")
        intro.setStyleSheet("font-size:17px;font-weight:600")
        layout.addWidget(intro)
        caption = QLabel("Permanece contando enquanto o HOME estiver aberto, mesmo em outra seção.")
        caption.setWordWrap(True)
        layout.addWidget(caption)
        self.display = QLabel("25:00")
        self.display.setStyleSheet("font-size:38px;font-weight:700;color:#FFFFFF")
        layout.addWidget(self.display)
        row = QHBoxLayout()
        self.duration = QSpinBox()
        self.duration.setRange(1,180)
        self.duration.setValue(25)
        self.duration.setSuffix(" min")
        row.addWidget(self.duration)
        start = QPushButton("Iniciar")
        start.clicked.connect(self.start)
        row.addWidget(start)
        layout.addLayout(row)
        row = QHBoxLayout()
        pause = QPushButton("Pausar / Continuar")
        pause.clicked.connect(self.pause_resume)
        row.addWidget(pause)
        stop = QPushButton("Encerrar")
        stop.clicked.connect(FOCUS.reset)
        row.addWidget(stop)
        layout.addLayout(row)
        self.status = QLabel("Pronto para começar.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()
        FOCUS.changed.connect(self.refresh)
        FOCUS.finished.connect(self.complete)
        self.refresh()

    def start(self):
        FOCUS.start(self.duration.value() * 60)

    def pause_resume(self):
        if FOCUS.active:
            FOCUS.pause()
        else:
            FOCUS.resume()

    def refresh(self):
        seconds = FOCUS.remaining
        self.display.setText(f"{seconds//60:02d}:{seconds%60:02d}")
        self.status.setText("Em concentração." if FOCUS.active else
                            "Pausado. Toque em continuar." if seconds else
                            "Pronto para começar.")
        self.duration.setEnabled(not FOCUS.active)

    def complete(self):
        self.status.setText("Sessão concluída. Bom trabalho!")

    def closeEvent(self, event):
        try:
            FOCUS.changed.disconnect(self.refresh)
            FOCUS.finished.disconnect(self.complete)
        except (RuntimeError, TypeError):
            pass
        super().closeEvent(event)
