"""Painel grafite do Home: controles compactos e responsivos, sem brilho neon."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QButtonGroup, QFrame, QSizePolicy, QGridLayout
)
from update_service import VERSION


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
                background: #242628; color: #f0f0f0;
                border: 1px solid #444648; border-radius: 13px;
                text-align: center; padding: 4px 2px;
                font-size: 11px; font-weight: 600;
            }
            QPushButton#actionCard:hover { background: #303235; border-color: #77797c; }
            QPushButton#actionCard:pressed { background: #191b1d; }
            QPushButton#actionCard:disabled { color: #888b8e; }
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
            QFrame#homePanel { background: #17181a; border: 1px solid #3d4042; border-radius: 19px; }
            QLabel { background: transparent; color: #e5e5e5; border: none; }
            QLabel#sub { color: #a5a6a8; font-size: 10px; }
            QLabel#small { color: #898b8e; font-size: 9px; }
            QLabel#title { font-size: 13px; font-weight: bold; }
            QPushButton#mood {
                background: #26282a; color: #c2c4c6;
                border: 1px solid #3c3e40; border-radius: 9px;
                padding: 5px 6px; font-size: 10px;
            }
            QPushButton#mood:checked { background: #4a4c4f; color: white; border-color: #66686a; }
            QPushButton#mood:hover { background: #393b3e; }
            QPushButton#more { background: transparent; color: #ddd; border: none; font-size: 15px; }
            QPushButton#more:hover { color: white; }
        """)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(15, 13, 15, 12)
        self.root.setSpacing(10)

        self.header = QWidget(self)
        self.header.setStyleSheet("background: transparent;")
        h = QHBoxLayout(self.header)
        h.setContentsMargins(0,0,0,0)
        h.setSpacing(8)
        self.smile = QLabel("☺")
        self.smile.setStyleSheet("font-size: 25px; color: #f0f0f0; background: transparent;")
        h.addWidget(self.smile)
        titles = QWidget()
        titles.setStyleSheet("background: transparent;")
        tl = QVBoxLayout(titles)
        tl.setContentsMargins(0,0,0,0)
        tl.setSpacing(1)
        title = QLabel("Expressão")
        title.setObjectName("title")
        self.subtitle = QLabel("Aparência e comportamento")
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
        self.line1.setStyleSheet("background:#383a3c; border:none; max-height:1px;")
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
        self.line2.setStyleSheet("background:#383a3c; border:none; max-height:1px;")
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
        self.root.setContentsMargins(10 if compact else 15,7 if compact else 13,10 if compact else 15,6 if compact else 12)
        self.root.setSpacing(5 if compact else 10)
        for card in (self.update_btn,self.edit_btn,self.interactions_btn,self.voice_btn,self.assistant_btn,self.quit_btn):
            card.set_content()
