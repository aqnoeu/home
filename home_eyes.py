"""HOME Windows: rendering and animation of the official animated eye pair.

Keep the eye geometry and voice/emotion animation independent of the shell,
settings pages and update mechanisms. Import EyesWidget from home for legacy API.
"""
import math
import random
import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget, QSizePolicy

class EyesWidget(QWidget):
    """Desenho proprio inspirado no conceito de olhos expressivos de robos."""
    MOODS = ('Normal', 'Feliz', 'Sonolento', 'Bravo')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(22)
        self.mood = 0
        self.emotion = "neutro"
        self.eye_color = QColor("#f2f8ff")
        self.emotion_height = 1.0
        self.emotion_width = 1.0
        self.eye_gap = 9
        self.gaze = 0.0
        self.target_gaze = 0.0
        self.gaze_y = 0.0
        self.target_gaze_y = 0.0
        now = time.monotonic()
        self._last_frame = now
        self.next_look = now + random.uniform(2.6, 4.2)
        self.next_blink = now + random.uniform(3.5, 6.0)
        self.last_click_blink = float('-inf')
        self.blink_duration = 0.38
        self.follow_mouse = False
        self.react_clicks = False
        self.voice_state = ''
        self.blink_begin = -1.0
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.animate)
        self.timer.start()

    def blink_on_click(self, now=None):
        """Uma reação discreta ao clique, sem piscar repetidamente em sequência."""
        now = time.monotonic() if now is None else now
        if now - self.last_click_blink < 1.25 or self.blink_begin >= 0:
            return False
        self.last_click_blink = now
        self.blink_begin = now
        self.next_blink = now + random.uniform(4.0, 7.0)
        return True

    def animate(self):
        now = time.monotonic()
        dt = max(0.0, min(now - self._last_frame, 0.15))
        self._last_frame = now
        if self.follow_mouse:
            from PySide6.QtGui import QCursor
            mouse = QCursor.pos()
            center = self.mapToGlobal(self.rect().center())
            dx = mouse.x() - center.x()
            dy = mouse.y() - center.y()
            self.target_gaze = max(-0.75, min(0.75, dx / max(240., self.width() * 2.5)))
            self.target_gaze_y = max(-0.45, min(0.45, dy / 420.))
        elif now >= self.next_look:
            self.target_gaze = random.choice([-0.45, -0.25, 0.0, 0.0, 0.25, 0.45])
            self.target_gaze_y = random.uniform(-0.22, 0.22)
            self.next_look = now + random.uniform(3.8, 7.0)
        # Suavização baseada em tempo real: mesma velocidade mesmo com atrasos do timer.
        weight = 1.0 - math.exp(-dt / 0.58)
        self.gaze += (self.target_gaze - self.gaze) * weight
        self.gaze_y += (self.target_gaze_y - self.gaze_y) * weight
        if now >= self.next_blink and self.blink_begin < 0:
            self.blink_begin = now
            self.next_blink = now + random.uniform(4.5, 8.0)
        if self.blink_begin >= 0 and now - self.blink_begin >= self.blink_duration:
            self.blink_begin = -1.0
        targets = {
            "neutro": (1., 1., QColor("#F2F8FF")),
            "raiva": (.82, 1., QColor("#FF6A00")),
            "sonolento": (.40, 1., QColor("#8EAFCF")),
            "tedio": (.75, .77, QColor("#8B95A4")),
            "carregando": (1., 1., QColor("#00C46A")),
            "bateria_baixa": (.86, 1., QColor("#F2A444")),
            "economia": (.72, 1., QColor("#93B8DB")),
        }
        hh, ww, color = targets.get(self.emotion, targets["neutro"])
        factor = min(1., dt * 5.5)
        self.emotion_height += (hh - self.emotion_height) * factor
        self.emotion_width += (ww - self.emotion_width) * factor
        r = self.eye_color.red() + (color.red() - self.eye_color.red()) * factor
        g = self.eye_color.green() + (color.green() - self.eye_color.green()) * factor
        b = self.eye_color.blue() + (color.blue() - self.eye_color.blue()) * factor
        self.eye_color = QColor(round(r), round(g), round(b))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if w < 20 or h < 12:
            return
        eh = min(h * 0.70, 34.0)
        ew = min(w * 0.21, eh * 0.82, 25.0) * self.emotion_width
        gap = max(0.0, min(float(self.eye_gap), w - 2 * ew - 8))
        left = w / 2 + self.gaze * min(10, w * .055) - (ew * 2 + gap) / 2
        blink = 1.0
        if self.blink_begin >= 0:
            progress = (time.monotonic() - self.blink_begin) / self.blink_duration
            blink = max(.07, 1.0 - math.sin(min(1., progress) * math.pi) * .95)
        if self.mood == 2 and self.emotion == "neutro":
            blink *= .54
        if self.voice_state == 'listening':
            height_factor = 1.08
        elif self.voice_state == 'thinking':
            height_factor = 0.72
        elif self.voice_state == 'speaking':
            # Fala: expressão estável, sem pulsação por frame.
            # A oscilação anterior (~2 Hz) parecia um loop de esticar/comprimir.
            height_factor = 0.96
        else:
            height_factor = 1.0
        blink *= height_factor
        height = max(2., eh * blink * self.emotion_height)
        for index in range(2):
            x = left + index * (ew + gap)
            if self.emotion == "raiva":
                x += math.sin(time.monotonic() * 24) * .55
            y = (h - height) / 2 + self.gaze_y * min(4.,h*.12)
            path = QPainterPath()
            radius = min(ew * .36, height * .45, 9)
            path.addRoundedRect(x, y, ew, height, radius, radius)
            fill = QColor(self.eye_color)
            if self.emotion == "carregando":
                fill.setAlpha(225 + round(15 * (1 + math.sin(time.monotonic()*2.6))))
            p.fillPath(path, fill)
            black = QColor('#05070b')
            if self.mood == 1 and self.emotion == "neutro" and blink > .6:
                p.setPen(Qt.NoPen)
                p.setBrush(black)
                p.drawEllipse(int(x-ew*.17), int(y+height*.49), int(ew*1.34), int(height*.81))
            elif (self.mood == 3 or self.emotion == "raiva") and blink > .6:
                lid = QPainterPath()
                lid.moveTo(x-2, y-2)
                lid.lineTo(x+ew+2, y-2)
                if index == 0:
                    lid.lineTo(x+ew+2, y+height*.43)
                    lid.lineTo(x-2, y+height*.06)
                else:
                    lid.lineTo(x+ew+2, y+height*.06)
                    lid.lineTo(x-2, y+height*.43)
                lid.closeSubpath()
                p.fillPath(lid, black)
        if self.emotion == "sonolento" and h > 55:
            p.setPen(QColor("#8EAFCF"))
            p.drawText(round(left + 2*ew + gap + 8), round(h*.34 - 7*math.sin(time.monotonic()*.9)), "z")


