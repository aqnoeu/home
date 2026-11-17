"""HOME Windows: standalone advanced geometry editing dialog."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QGroupBox, QSpinBox, QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout

class EditDialog(QDialog):
    def __init__(self, home):
        super().__init__(None)
        self.home = home
        self.setWindowTitle('Home — Modo Edicao')
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(330)
        self.setStyleSheet("""
            QDialog {background:#0B111A;color:white}
            QLabel,QGroupBox {color:#FFFFFF}
            QGroupBox {border:1px solid #374251;border-radius:8px;margin-top:9px;padding:10px}
            QGroupBox::title {subcontrol-origin:margin;left:10px;padding:0 5px}
            QSpinBox {background:#1C2737;color:white;border:1px solid #324357;border-radius:5px;padding:5px}
            QPushButton {color:white;background:#1C2737;padding:9px;border-radius:7px}
            QPushButton:hover {background:#26384F}
        """)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Arraste as alcas da direita e de baixo.\nAlterne entre os tamanhos recolhido e expandido.'))
        self.inputs = {}
        groups = [
            ('Recolhido', [('closed_w', 'Largura', 115, 650), ('closed_h', 'Altura', 18, 110)]),
            ('Expandido', [('open_w', 'Largura', 380, 850), ('open_h', 'Altura', 265, 650)]),
            ('Posicao', [('offset', 'Distancia da esquerda', 0, 5000)])
        ]
        for title, fields in groups:
            group = QGroupBox(title)
            form = QFormLayout(group)
            for key, caption, minimum, maximum in fields:
                spin = QSpinBox()
                spin.setRange(minimum, maximum)
                spin.setSuffix(' px')
                spin.setValue(home.settings[key])
                spin.valueChanged.connect(lambda value, k=key: self.home.change_setting(k, value))
                self.inputs[key] = spin
                form.addRow(caption, spin)
            layout.addWidget(group)
        self.switch_btn = QPushButton()
        self.switch_btn.clicked.connect(self.switch)
        layout.addWidget(self.switch_btn)
        buttons = QHBoxLayout()
        reset = QPushButton('Restaurar padrao')
        reset.clicked.connect(self.reset)
        finish = QPushButton('Concluir edicao')
        finish.clicked.connect(self.accept)
        buttons.addWidget(reset)
        buttons.addWidget(finish)
        layout.addLayout(buttons)
        self.sync()
        b = home.screen.availableGeometry()
        self.move(min(max(home.x()+home.width()+16,b.left()),b.right()-330),
                  min(max(home.y()+50,b.top()),b.bottom()-440))

    def switch(self):
        self.home.toggle()
        self.sync()

    def sync(self):
        self.switch_btn.setText('Editar tamanho RECOLHIDO' if self.home.expanded else 'Editar tamanho EXPANDIDO')
        for key, spin in self.inputs.items():
            spin.blockSignals(True)
            spin.setValue(self.home.settings[key])
            spin.blockSignals(False)

    def reset(self):
        self.home.settings.update(self.home.DEFAULTS)
        self.home.apply_settings()
        self.sync()


