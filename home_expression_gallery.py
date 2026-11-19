"""HOME expression manager: persistent real-notch selection and reversible hiding."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout
from home_eyes import EyesWidget

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
    """Two rows, three columns, pagination, hide/restore and live persisted choice."""
    def __init__(self, home, parent=None):
        super().__init__(parent)
        self.home = home
        self.page = 0
        self.selected = home.settings.get("selected_expression", 0)
        self.show_hidden = False
        self.setStyleSheet("""
            QLabel{color:#DDE7F4;background:transparent}
            QPushButton{background:#1C2737;color:#DDE7F4;border:1px solid #34465A;
                         border-radius:10px;padding:9px;font-size:12px}
            QPushButton:checked{background:#2F6BFF;color:#FFFFFF;border-color:#2F6BFF}
            QPushButton:disabled{color:#64748B}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(9)
        self.preview = EyesWidget(self)
        self.preview.setFixedHeight(90)
        self.preview.eye_gap = home.settings.get("eye_gap", 9)
        self.preview.follow_mouse = False
        layout.addWidget(self.preview)
        self.current_label = QLabel()
        self.current_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.current_label)
        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        layout.addLayout(self.grid)
        pager = QHBoxLayout()
        self.previous = QPushButton("‹")
        self.previous.clicked.connect(lambda: self.change_page(-1))
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignCenter)
        self.next = QPushButton("›")
        self.next.clicked.connect(lambda: self.change_page(1))
        pager.addWidget(self.previous)
        pager.addWidget(self.page_label, 1)
        pager.addWidget(self.next)
        layout.addLayout(pager)
        controls = QHBoxLayout()
        self.hide_button = QPushButton("Ocultar selecionada")
        self.hide_button.clicked.connect(self.hide_selected)
        self.restore_button = QPushButton("Gerenciar ocultas")
        self.restore_button.clicked.connect(self.toggle_hidden)
        self.auto_button = QPushButton("Modo automático")
        self.auto_button.clicked.connect(self.use_auto)
        controls.addWidget(self.hide_button)
        controls.addWidget(self.restore_button)
        controls.addWidget(self.auto_button)
        layout.addLayout(controls)
        self.note = QLabel("A escolha é aplicada ao notch real. Ocultar não apaga uma expressão.")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        layout.addStretch()
        self.display_preview(self.selected)
        self.render_buttons()

    def visible_indices(self):
        hidden = set(self.home.settings.get("hidden_expressions", []))
        return [i for i in range(len(EXPRESSIONS)) if (i in hidden) == self.show_hidden]

    def display_preview(self, index):
        name, emotion, mood = EXPRESSIONS[index]
        self.preview.mood = mood
        self.preview.emotion = emotion
        self.preview.preview_emotion = None
        if emotion in EyesWidget.EXTRA_EXPRESSIONS:
            self.preview.show_expression(emotion, seconds=86400)
        self.preview.update()
        self.current_label.setText("Expressão: " + name)

    def select(self, index):
        if self.show_hidden:
            if self.home.set_expression_visible(index, True):
                self.show_hidden = False
                self.selected = index
                self.home.select_expression(index)
                self.note.setText("Expressão restaurada e aplicada ao Home.")
        elif self.home.select_expression(index):
            self.selected = index
            self.note.setText("Expressão selecionada e fixada no notch real.")
        self.display_preview(self.selected)
        self.render_buttons()

    def hide_selected(self):
        if self.show_hidden:
            return
        if self.home.set_expression_visible(self.selected, False):
            visible = self.visible_indices()
            self.selected = visible[0] if visible else 0
            self.display_preview(self.selected)
            self.note.setText("Expressão ocultada; restaure em Gerenciar ocultas.")
        else:
            self.note.setText("Mantenha pelo menos uma expressão disponível.")
        self.render_buttons()

    def toggle_hidden(self):
        self.show_hidden = not self.show_hidden
        self.page = 0
        self.restore_button.setText("Voltar à galeria" if self.show_hidden else "Gerenciar ocultas")
        self.note.setText("Clique numa expressão oculta para restaurá-la." if self.show_hidden
                          else "Selecione uma expressão para aplicá-la ao notch real.")
        self.render_buttons()

    def use_auto(self):
        self.home.use_automatic_expressions()
        self.note.setText("Modo automático ativo: contexto, voz e bateria controlam os olhos.")

    def change_page(self, direction):
        count = len(self.visible_indices())
        pages = max(1, (count + 5)//6)
        self.page = max(0, min(pages-1, self.page+direction))
        self.render_buttons()

    def render_buttons(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        indices = self.visible_indices()
        pages = max(1, (len(indices)+5)//6)
        self.page = max(0, min(self.page, pages-1))
        for slot, index in enumerate(indices[self.page*6:(self.page+1)*6]):
            button = QPushButton(EXPRESSIONS[index][0])
            button.setCheckable(True)
            button.setChecked(not self.show_hidden and index == self.home.settings.get("selected_expression", 0))
            button.clicked.connect(lambda checked=False, i=index: self.select(i))
            button.setToolTip("Restaurar expressão" if self.show_hidden else "Selecionar e fixar no Home")
            self.grid.addWidget(button, slot//3, slot%3)
        self.page_label.setText(f"Página {self.page + 1} de {pages}")
        self.previous.setEnabled(self.page>0)
        self.next.setEnabled(self.page+1<pages)
        self.hide_button.setEnabled(not self.show_hidden and len(indices)>1)
