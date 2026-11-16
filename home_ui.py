"""Painel grafite do Home: controles compactos e responsivos, sem brilho neon."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from pathlib import Path
import sys
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QButtonGroup, QFrame, QSizePolicy, QGridLayout
)
from update_service import VERSION
from collections import deque
from PySide6.QtGui import QImage


def load_transparent_home_logo(path):
    """Remove apenas o fundo claro conectado às bordas, preservando os olhos."""
    image = QImage(str(path))
    if image.isNull():
        return QPixmap()
    image = image.convertToFormat(QImage.Format_ARGB32)
    width, height = image.width(), image.height()
    queue = deque()
    visited = set()
    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y))
        color = image.pixelColor(x, y)
        if min(color.red(), color.green(), color.blue()) < 220:
            continue
        color.setAlpha(0)
        image.setPixelColor(x, y, color)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                queue.append((nx, ny))
    return QPixmap.fromImage(image)




class ActionCard(QPushButton):
    def __init__(self, symbol, title, subtitle, parent=None):
        super().__init__(parent)
        self.symbol, self.title, self.subtitle = symbol, title, subtitle
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("actionCard")
        self.setMinimumHeight(48)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("""
            QPushButton#actionCard {
                background: #1C2737; color: #FFFFFF;
                border: 1px solid #34455B; border-radius: 13px;
                text-align: center; padding: 4px 2px;
                font-size: 11px; font-weight: 600;
            }
            QPushButton#actionCard:hover { background: #26384F; border-color: #2F6BFF; }
            QPushButton#actionCard:pressed { background: #101B29; }
            QPushButton#actionCard:disabled { color: #9FAFC4; }
        """)
        self.set_content()

    def set_content(self):
        if self.height() < 78:
            self.setText(f"{self.symbol}  {self.title}")
        else:
            self.setText(f"{self.symbol}\n{self.title}\n{self.subtitle}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.set_content()


class HomePanel(QFrame):
    mood_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homePanel")
        self.setStyleSheet("""
            QFrame#homePanel { background: #0B111A; border: 1px solid #324357; border-radius: 19px; }
            QLabel { background: transparent; color: #FFFFFF; border: none; }
            QLabel#sub { color: #A8B6C8; font-size: 10px; }
            QLabel#small { color: #A0AEC0; font-size: 9px; }
            QLabel#title { font-size: 13px; font-weight: bold; }
            QPushButton#mood {
                background: #1C2737; color: #DDE7F4;
                border: 1px solid #34465A; border-radius: 9px;
                padding: 5px 6px; font-size: 10px;
            }
            QPushButton#mood:checked { background: #2F6BFF; color: white; border-color: #2F6BFF; }
            QPushButton#mood:hover { background: #26384F; }
            QPushButton#more { background: transparent; color: #ddd; border: none; font-size: 15px; }
            QPushButton#more:hover { color: #FF6A00; }
        """)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(17, 16, 17, 14)
        self.root.setSpacing(12)

        self.header = QWidget(self)
        self.header.setStyleSheet("background: transparent;")
        h = QHBoxLayout(self.header)
        h.setContentsMargins(0,0,0,0)
        h.setSpacing(8)
        self.smile = QLabel()
        self.smile.setStyleSheet("color:#FFFFFF;font-size:12px;font-weight:700;background:transparent")
        icon_path = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets" / "home_icon_approved.png"
        image = load_transparent_home_logo(icon_path) if icon_path.is_file() else QPixmap()
        if not image.isNull():
            self.smile.setFixedSize(44,44)
            self.smile.setPixmap(image.scaled(
                44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.smile.setAlignment(Qt.AlignCenter)
        else:
            self.smile.setText("HOME")
            self.smile.setStyleSheet("color:#FFFFFF;font-size:15px;font-weight:700")
        self.smile.setToolTip("Símbolo oficial HOME")
        h.addWidget(self.smile)
        titles = QWidget()
        titles.setStyleSheet("background: transparent;")
        tl = QVBoxLayout(titles)
        tl.setContentsMargins(0,0,0,0)
        tl.setSpacing(1)
        title = QLabel("HOME  ·  Expressões")
        title.setObjectName("title")
        self.subtitle = QLabel("Um assistente para você.")
        self.subtitle.setStyleSheet("color:#FF6A00;font-size:10px;font-weight:500")
        self.subtitle.setObjectName("sub")
        tl.addWidget(title)
        tl.addWidget(self.subtitle)
        h.addWidget(titles, 1)

        self.mood_group = QButtonGroup(self)
        self.mood_group.setExclusive(True)
        self.mood_buttons=[]
        for index, name in enumerate(("Normal", "Amigável", "Focada")):
            b=QPushButton(name)
            b.setObjectName("mood")
            b.setCheckable(True)
            b.setChecked(index == 0)
            b.setCursor(Qt.PointingHandCursor)
            self.mood_group.addButton(b, index)
            self.mood_buttons.append(b)
            h.addWidget(b)
        self.more=QPushButton("⋯")
        self.more.setObjectName("more")
        self.more.setToolTip("Alternar entre as expressões adicionais")
        self.more.setCursor(Qt.PointingHandCursor)
        h.addWidget(self.more)
        self.mood_group.idClicked.connect(self.mood_changed.emit)
        self.root.addWidget(self.header, 0)

        self.line1 = QFrame()
        self.line1.setFrameShape(QFrame.HLine)
        self.line1.setStyleSheet("background:#324357; border:none; max-height:1px;")
        self.root.addWidget(self.line1)

        self.cards = QWidget()
        self.cards.setStyleSheet("background:transparent;")
        row=QGridLayout(self.cards)
        row.setContentsMargins(0,0,0,0)
        row.setSpacing(7)
        self.update_btn=ActionCard("↻", "Atualizações", "Verificar novas versões")
        self.edit_btn=ActionCard("⤢", "Modo edição", "Ajustar tamanho")
        self.interactions_btn=ActionCard("⌘", "Interações", "Windows e Chrome")
        self.voice_btn=ActionCard("◉", "Voz e microfone", "Ei, Home / botão")
        self.assistant_btn=ActionCard("✎", "Assistente", "Digite e ouça respostas")
        self.quit_btn=ActionCard("⏻", "Encerrar", "Fechar o Home")
        row.addWidget(self.update_btn, 0, 0)
        row.addWidget(self.edit_btn, 0, 1)
        row.addWidget(self.interactions_btn, 1, 0)
        row.addWidget(self.voice_btn, 1, 1)
        row.addWidget(self.assistant_btn, 2, 0)
        row.addWidget(self.quit_btn, 2, 1)
        self.root.addWidget(self.cards, 1)

        self.line2 = QFrame()
        self.line2.setFrameShape(QFrame.HLine)
        self.line2.setStyleSheet("background:#324357; border:none; max-height:1px;")
        self.root.addWidget(self.line2)

        self.footer=QWidget()
        self.footer.setStyleSheet("background:transparent;")
        foot=QHBoxLayout(self.footer)
        foot.setContentsMargins(0,0,0,0)
        self.credit=QLabel("⌘  Desenvolvido com @aqnoeu")
        self.credit.setObjectName("small")
        foot.addWidget(self.credit)
        foot.addStretch()
        self.mic_status = QLabel("")
        self.mic_status.setObjectName("small")
        self.mic_status.setToolTip("O microfone só escuta quando você ativa a permissão")
        foot.addWidget(self.mic_status)
        self.version=QLabel(f"v{VERSION}")
        self.version.setObjectName("small")
        foot.addWidget(self.version)
        self.root.addWidget(self.footer)

    def set_mood(self, index):
        if index in (0,1,2):
            self.mood_buttons[index].setChecked(True)
        else:
            self.mood_group.setExclusive(False)
            for button in self.mood_buttons: button.setChecked(False)
            self.mood_group.setExclusive(True)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        compact = self.width() < 420 or self.height() < 245
        self.subtitle.setVisible(not compact)
        self.smile.setVisible(not compact)
        self.more.setVisible(not compact)
        self.root.setContentsMargins(11 if compact else 17,9 if compact else 16,11 if compact else 17,8 if compact else 14)
        self.root.setSpacing(7 if compact else 12)
        for card in (self.update_btn,self.edit_btn,self.interactions_btn,self.voice_btn,self.assistant_btn,self.quit_btn):
            card.set_content()
