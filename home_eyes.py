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
    EXTRA_EXPRESSIONS = ('piscadela', 'lovabow', 'pensando', 'surpreso',
                         'desconfiado', 'timido', 'confuso', 'travesso')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(22)
        self.mood = 0
        self.emotion = "neutro"
        self.preview_emotion = None
        self.preview_until = 0.0
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

    def show_expression(self, name, seconds=12.0):
        """Previa temporaria para o catalogo; contexto automatico permanece ativo."""
        if name not in self.EXTRA_EXPRESSIONS:
            return False
        self.preview_emotion = name
        self.preview_until = time.monotonic() + max(0.0, seconds)
        self.update()
        return True

    def current_expression(self, now=None):
        now = time.monotonic() if now is None else now
        if self.preview_emotion and now < self.preview_until:
            return self.preview_emotion
        self.preview_emotion = None
        return self.emotion

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
        active = self.current_expression(now)
        targets = {
            "neutro": (1., 1., QColor("#F2F8FF")),
            "raiva": (.82, 1., QColor("#FF6A00")),
            "sonolento": (.40, 1., QColor("#8EAFCF")),
            "tedio": (.75, .77, QColor("#8B95A4")),
            "carregando": (1., 1., QColor("#00C46A")),
            "bateria_baixa": (.86, 1., QColor("#F2A444")),
            "economia": (.72, 1., QColor("#93B8DB")),
            "piscadela": (1., 1., QColor("#F2F8FF")),
            "lovabow": (1., 1., QColor("#F2F8FF")),
            "pensando": (.76, .92, QColor("#D5E4F5")),
            "surpreso": (1.12, 1.06, QColor("#F2F8FF")),
            "desconfiado": (.82, .9, QColor("#DDE8F8")),
            "timido": (.8, .94, QColor("#E8C4D4")),
            "confuso": (.9, .96, QColor("#DFE9F8")),
            "travesso": (.84, .94, QColor("#F2F8FF")),
        }
        hh, ww, color = targets.get(active, targets["neutro"])
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
        active = self.current_expression()
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
            if active == "raiva":
                x += math.sin(time.monotonic() * 24) * .55
            eye_height = height
            if active == "piscadela" and index == 0:
                eye_height *= .12
            elif active == "confuso":
                eye_height *= (.65 if index == 0 else 1.08)
            elif active == "desconfiado":
                eye_height *= (.62 if index == 0 else .96)
            elif active == "travesso":
                eye_height *= (.55 if index == 0 else .92)
            if active == "pensando":
                x += ew * .12
            y = (h - eye_height) / 2 + self.gaze_y * min(4.,h*.12)
            path = QPainterPath()
            radius = min(ew * .36, eye_height * .45, 9)
            path.addRoundedRect(x, y, ew, eye_height, radius, radius)
            fill = QColor(self.eye_color)
            if active == "carregando":
                fill.setAlpha(225 + round(15 * (1 + math.sin(time.monotonic()*2.6))))
            if active == "lovabow":
                # O coracao substitui cada olho; nao existe boca.
                path = QPainterPath()
                path.moveTo(x + ew*.5, y + eye_height*.93)
                path.cubicTo(x-ew*.14, y+eye_height*.59, x-ew*.1, y+eye_height*.12, x+ew*.26, y+eye_height*.12)
                path.cubicTo(x+ew*.43, y+eye_height*.12, x+ew*.5, y+eye_height*.29, x+ew*.5, y+eye_height*.29)
                path.cubicTo(x+ew*.5, y+eye_height*.29, x+ew*.57, y+eye_height*.12, x+ew*.74, y+eye_height*.12)
                path.cubicTo(x+ew*1.1, y+eye_height*.12, x+ew*1.14, y+eye_height*.59, x+ew*.5, y+eye_height*.93)
                path.closeSubpath()
                phase = (time.monotonic()*.6) % 1.
                fill = QColor("#F2F8FF" if phase < .25 else "#F6AEC8" if phase < .5 else "#F18BB5")
            p.fillPath(path, fill)
            black = QColor('#05070b')
            if self.mood == 1 and active == "neutro" and blink > .6:
                p.setPen(Qt.NoPen)
                p.setBrush(black)
                p.drawEllipse(int(x-ew*.17), int(y+height*.49), int(ew*1.34), int(height*.81))
            elif (self.mood == 3 or active == "raiva") and blink > .6:
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
        if active == "lovabow" and h >= 32:
            # Pequenos coracoes sobem apenas na fase final; somem no notch compacto.
            phase = (time.monotonic() * .6) % 1.
            if phase >= .5:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#F18BB5"))
                for i in range(3):
                    cx = left + 2*ew + gap + 3 + i*5
                    cy = h*.67 - (phase-.5)*h*.5 - i*3
                    spark = QPainterPath()
                    spark.moveTo(cx, cy+3)
                    spark.cubicTo(cx-5, cy, cx-3, cy-3, cx, cy-1)
                    spark.cubicTo(cx+3, cy-3, cx+5, cy, cx, cy+3)
                    spark.closeSubpath()
                    p.fillPath(spark, QColor("#F18BB5"))
        if active in ("sonolento", "timido") and h >= 28:
            # Tracos laterais abaixo dos olhos, sem formar boca ou rosto.
            p.setPen(QColor("#8EAFCF" if active == "sonolento" else "#E8C4D4"))
            for base_x in (left - 3, left + ew + gap + ew + 1):
                for offset in (0, 4):
                    yy = h*.80 + offset*.23
                    p.drawLine(round(base_x+offset), round(yy),
                               round(base_x+offset+2), round(yy+2))
        if active == "sonolento" and h > 32:
            p.setPen(QColor("#8EAFCF"))
            p.drawText(round(left + 2*ew + gap + 8), round(h*.34 - 7*math.sin(time.monotonic()*.9)), "z")


