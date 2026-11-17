"""Galeria de expressões do HOME para Windows, sem boca e com grade compacta."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout
from home_eyes import EyesWidget

# Quatro expressões legadas + oito variantes do catálogo oficial.
EXPRESSIONS = (
    ("Normal", "neutro", 0),
    ("Feliz", "neutro", 1),
    ("Sonolento", "sonolento", 2),
    ("Bravo", "raiva", 3),
    ("Piscadela", "piscadela", 0),
    ("Lovabow", "lovabow", 0),
    ("Pensando", "pensando", 0),
    ("Surpreso", "surpreso", 0),
    ("Desconfiado", "desconfiado", 0),
    ("Tímido", "timido", 0),
    ("Confuso", "confuso", 0),
    ("Travesso", "travesso", 0),
)

class ExpressionGallery(QWidget):
    """Duas linhas x três colunas, duas páginas, prévia com o renderizador verdadeiro."""
    def __init__(self, home, parent=None):
        super().__init__(parent)
        self.home = home
        self.page = 0
        self.selected = 0
        self.setStyleSheet("""
            QLabel{color:#DDE7F4;background:transparent}
            QPushButton{background:#1C2737;color:#DDE7F4;border:1px solid #34465A;
                         border-radius:10px;padding:10px;font-size:12px}
            QPushButton:checked{background:#2F6BFF;color:#FFFFFF;border-color:#2F6BFF}
            QPushButton:disabled{color:#64748B}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(13)
        title = QLabel("Escolha uma expressão para visualizar no Home.")
        title.setWordWrap(True)
        layout.addWidget(title)
        self.preview = EyesWidget(self)
        self.preview.setFixedHeight(105)
        self.preview.eye_gap = home.settings.get("eye_gap", 9)
        self.preview.follow_mouse = False
        self.preview.react_clicks = False
        layout.addWidget(self.preview)
        self.current_label = QLabel()
        self.current_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.current_label)
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(7)
        self.grid.setVerticalSpacing(7)
        layout.addLayout(self.grid)
        pager = QHBoxLayout()
        self.previous = QPushButton("‹")
        self.previous.setFixedWidth(60)
        self.previous.clicked.connect(lambda: self.change_page(-1))
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.next = QPushButton("›")
        self.next.setFixedWidth(60)
        self.next.clicked.connect(lambda: self.change_page(1))
        pager.addWidget(self.previous)
        pager.addWidget(self.page_label, 1)
        pager.addWidget(self.next)
        layout.addLayout(pager)
        note = QLabel("Prévia temporária no notch; os estados de bateria e voz permanecem independentes.")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        self.select(0, apply=False)
        self.render_buttons()

    def select(self, index, apply=True):
        self.selected = index
        name, emotion, mood = EXPRESSIONS[index]
        self.preview.mood = mood
        self.preview.emotion = emotion
        self.preview.preview_emotion = None
        if emotion in EyesWidget.EXTRA_EXPRESSIONS:
            self.preview.show_expression(emotion, seconds=86400)
        self.preview.update()
        self.current_label.setText("Expressão: " + name)
        if apply:
            self.home.eyes.mood = mood
            if emotion in EyesWidget.EXTRA_EXPRESSIONS:
                self.home.eyes.show_expression(emotion, seconds=12)
            else:
                # The context engine still owns automatic state transitions.
                self.home.eyes.preview_emotion = None
                self.home.eyes.emotion = emotion
                self.home.eyes.update()
        self.render_buttons()

    def change_page(self, direction):
        self.page = max(0, min(1, self.page + direction))
        self.render_buttons()

    def render_buttons(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        for slot, index in enumerate(range(self.page * 6, min((self.page + 1) * 6, len(EXPRESSIONS)))):
            name = EXPRESSIONS[index][0]
            button = QPushButton(name)
            button.setCheckable(True)
            button.setChecked(index == self.selected)
            button.clicked.connect(lambda checked=False, i=index: self.select(i))
            self.grid.addWidget(button, slot // 3, slot % 3)
        self.page_label.setText(f"Página {self.page + 1} de 2")
        self.previous.setEnabled(self.page > 0)
        self.next.setEnabled(self.page < 1)
