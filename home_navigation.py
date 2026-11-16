"""Navegação interna do Home: páginas incorporadas ao entalhe expandido."""
from PySide6.QtCore import Qt, Signal
from update_service import VERSION
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QGridLayout,
    QScrollArea, QFormLayout, QSpinBox, QFrame, QSizePolicy
)


class EditPage(QWidget):
    def __init__(self, home, parent=None):
        super().__init__(parent)
        self.home = home
        self.setStyleSheet("""QWidget{background:transparent;color:#eee}
            QLabel{color:#ccc}
            QSpinBox{background:#282a2d;color:#fff;border:1px solid #4c4f51;border-radius:8px;padding:6px}
            QPushButton{background:#303235;color:white;border:1px solid #505255;border-radius:9px;padding:8px}
            QPushButton:hover{background:#44464a}
        """)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel("Ajuste os tamanhos do Home e sua distância da esquerda."))
        layout.addWidget(QLabel("As mudanças são salvas automaticamente; volte ao Hub para ver o tamanho usual."))
        form=QFormLayout()
        self.inputs={}
        for key,title,limits in [
            ("closed_w","Recolhido · largura",(115,650)),
            ("closed_h","Recolhido · altura",(18,110)),
            ("open_w","Hub · largura",(380,850)),
            ("open_h","Hub · altura",(265,650)),
            ("offset","Posição · distância da esquerda",(0,5000))
        ]:
            spin=QSpinBox()
            spin.setRange(*limits)
            spin.setSuffix(" px")
            spin.setValue(home.settings[key])
            spin.valueChanged.connect(lambda value,k=key: home.change_setting(k,value))
            form.addRow(title,spin)
            self.inputs[key]=spin
        layout.addLayout(form)
        btn=QPushButton("Restaurar tamanhos padrão")
        btn.clicked.connect(self.reset)
        layout.addWidget(btn)
        layout.addStretch()

    def sync(self):
        for key, spin in self.inputs.items():
            spin.blockSignals(True)
            spin.setValue(self.home.settings[key])
            spin.blockSignals(False)

    def reset(self):
        self.home.settings.update(self.home.DEFAULTS)
        self.home.apply_settings()
        self.sync()


class Workspace(QWidget):
    requested = Signal(str)

    SECTIONS = (
        ("hub","⌂ Hub"),("assistant","✎ Assistente"),("voice","◉ Voz"),
        ("integrations","⌘ Interações"),("edit","⤢ Edição"),
        ("updates","↻ Atualizações"),("exit","⏻ Encerrar"),
    )

    def __init__(self,home,parent=None):
        super().__init__(parent)
        self.home=home
        self.section="hub"
        self.current=None
        self._stretch=None
        self.setStyleSheet("""
            QWidget#workspace{background:#17181a;border:1px solid #3d4042;border-radius:19px}
            QWidget#pagehost{background:transparent;border:none}
            QLabel{background:transparent;color:#ddd;border:none}
            QPushButton#nav{background:#27292b;border:1px solid #3d3f41;border-radius:8px;
                            padding:7px 6px;color:#c9cbcc;font-size:11px}
            QPushButton#nav:checked{background:#505256;color:white;border-color:#6c6d70}
            QPushButton#nav:hover{background:#3a3c40}
            QPushButton#primary{background:#303235;border:1px solid #57595c;border-radius:9px;
                                color:white;padding:12px}
            QPushButton#primary:hover{background:#44464a}
        """)
        self.setObjectName("workspace")
        outer=QVBoxLayout(self)
        outer.setContentsMargins(15,12,15,12)
        outer.setSpacing(10)
        title=QHBoxLayout()
        self.heading=QLabel("Home")
        self.heading.setStyleSheet("font-size:16px;font-weight:bold")
        title.addWidget(self.heading)
        title.addStretch()
        self.back=QPushButton("← Voltar ao Hub")
        self.back.setObjectName("nav")
        self.back.clicked.connect(lambda:self.requested.emit("hub"))
        title.addWidget(self.back)
        outer.addLayout(title)
        nav=QGridLayout()
        nav.setSpacing(5)
        self.navbuttons={}
        for i,(section,caption) in enumerate(self.SECTIONS):
            button=QPushButton(caption)
            button.setObjectName("nav")
            button.setCheckable(True)
            button.clicked.connect(lambda _=False,name=section:self.requested.emit(name))
            nav.addWidget(button,i//3,i%3)
            self.navbuttons[section]=button
        outer.addLayout(nav)
        self.scroll=QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea{background:transparent;border:0} QScrollBar:vertical{width:8px}")
        self.host=QWidget()
        self.host.setObjectName("pagehost")
        self.host_layout=QVBoxLayout(self.host)
        self.host_layout.setContentsMargins(2,3,2,3)
        self.scroll.setWidget(self.host)
        outer.addWidget(self.scroll,1)
        self.footer=QLabel(f"Desenvolvido com @aqnoeu   ·   v{VERSION}")
        self.footer.setStyleSheet("color:#858689;font-size:10px")
        outer.addWidget(self.footer)

    def set_section(self,section):
        if self.current is not None:
            old=self.current
            self.current=None
            self.host_layout.removeWidget(old)
            if self._stretch is not None:
                self.host_layout.removeItem(self._stretch)
                self._stretch=None
            if hasattr(old,"disconnect_signals"):
                old.disconnect_signals()
            if hasattr(old,"home") and hasattr(old,"page_text"):
                try:old.home.chrome_bridge.received.disconnect(old.on_page)
                except (RuntimeError,TypeError):pass
            old.hide()
            old.deleteLater()
        self.section=section
        for name,button in self.navbuttons.items():
            button.setChecked(section==name)
        titles={"assistant":"Assistente — Digite e ouça","voice":"Voz e microfone","integrations":"Interações com Windows e Chrome",
                "edit":"Modo edição","updates":"Atualizações","exit":"Encerrar o Home"}
        self.heading.setText(titles.get(section,"Home"))
        if section=="assistant":
            from home_assistant import AssistantPage
            page=AssistantPage(self.home)
        elif section=="voice":
            from home_voice import VoiceDialog
            page=VoiceDialog(self.home)
        elif section=="integrations":
            from home_integrations import IntegrationsDialog
            page=IntegrationsDialog(self.home)
        elif section=="edit":
            page=EditPage(self.home)
        elif section=="updates":
            page=self.updates_page()
        elif section=="exit":
            page=self.exit_page()
        else:
            return
        # QDialog também pode ser incorporado com flags Qt.Widget; sem exec() ou janela separada.
        page.setParent(self.host)
        page.setWindowFlags(Qt.Widget)
        page.setMinimumSize(0,0)
        page.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred)
        for button in page.findChildren(QPushButton):
            if button.text() in ("Concluir","Concluir edicao"):
                button.clicked.connect(lambda:self.requested.emit("hub"))
        self.host_layout.addWidget(page)
        self.host_layout.addStretch()
        self._stretch=self.host_layout.itemAt(self.host_layout.count()-1)
        self.current=page
        page.show()
        self.scroll.verticalScrollBar().setValue(0)

    def updates_page(self):
        page=QWidget()
        layout=QVBoxLayout(page)
        description=QLabel("O Home verifica versões oficiais no GitHub. A instalação só começa com sua autorização.")
        description.setWordWrap(True)
        layout.addWidget(description)
        self.update_status=QLabel("Versão instalada: "+self.home.windowTitle().replace("Home ",""))
        self.update_status.setWordWrap(True)
        layout.addWidget(self.update_status)
        button=QPushButton("Verificar atualizações")
        button.setObjectName("primary")
        button.clicked.connect(self.check_updates)
        layout.addWidget(button)
        self.install_btn=QPushButton("Instalar versão disponível")
        self.install_btn.setObjectName("primary")
        self.install_btn.setVisible(bool(self.home.available_update))
        self.install_btn.clicked.connect(self.show_confirmation)
        layout.addWidget(self.install_btn)
        android_btn=QPushButton("Home para Android — QR Code")
        android_btn.setObjectName("primary")
        android_btn.clicked.connect(self.show_android_qr)
        layout.addWidget(android_btn)
        self.confirm=QWidget()
        row=QHBoxLayout(self.confirm)
        row.addWidget(QLabel("Autoriza baixar e reiniciar o Home?"))
        yes=QPushButton("Sim, instalar")
        yes.clicked.connect(self.install_update)
        no=QPushButton("Cancelar")
        no.clicked.connect(self.confirm.hide)
        row.addWidget(yes)
        row.addWidget(no)
        self.confirm.hide()
        layout.addWidget(self.confirm)
        layout.addStretch()
        return page

    def show_android_qr(self):
        """QR Code permanente para a pagina oficial de downloads, sem pareamento com PC."""
        import qrcode
        from PySide6.QtGui import QColor, QPainter, QPixmap
        from PySide6.QtWidgets import QDialog
        url = "https://github.com/aqnoeu/home/releases"
        qr = qrcode.QRCode(border=2, box_size=1,
                            error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(url)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        cell = 7
        side = len(matrix) * cell
        pixmap = QPixmap(side, side)
        pixmap.fill(QColor("white"))
        painter = QPainter(pixmap)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#08090b"))
        for y, line in enumerate(matrix):
            for x, is_black in enumerate(line):
                if is_black:
                    painter.drawRect(x*cell, y*cell, cell, cell)
        painter.end()
        popup = QDialog(self)
        popup.setWindowTitle("Home para Android")
        popup.setStyleSheet("QDialog{background:#17181a;color:#eeeeee} QLabel{color:#eeeeee}")
        layout = QVBoxLayout(popup)
        info = QLabel("Escaneie para abrir as Releases do Home.\\n"
                      "Quando houver APK publicado, selecione Home-Android.apk.")
        info.setWordWrap(True)
        layout.addWidget(info)
        image = QLabel()
        image.setPixmap(pixmap)
        image.setAlignment(Qt.AlignCenter)
        layout.addWidget(image)
        close = QPushButton("Fechar")
        close.clicked.connect(popup.accept)
        layout.addWidget(close)
        popup.exec()

    def check_updates(self):
        self.update_status.setText("Consultando GitHub...")
        self.home.run_worker("check")

    def update_result(self,info):
        if self.section != "updates":return
        self.update_status.setText("Nova versão: "+info["version"] if info
                                  else "Você já está na versão mais recente publicada.")
        self.install_btn.setVisible(bool(info))
        self.confirm.hide()

    def update_failed(self,error):
        if self.section=="updates":
            self.update_status.setText("Atualização indisponível: "+error)

    def show_confirmation(self):
        if self.home.available_update:
            self.confirm.show()

    def install_update(self):
        if not self.home.available_update:return
        self.confirm.hide()
        self.update_status.setText("Baixando atualização autorizada...")
        self.home.run_worker("download",self.home.available_update)

    def exit_page(self):
        page=QWidget()
        l=QVBoxLayout(page)
        l.addWidget(QLabel("Você pode recolher o Home sem encerrar o aplicativo."))
        close=QPushButton("Recolher e continuar")
        close.setObjectName("primary")
        close.clicked.connect(self.home.collapse)
        l.addWidget(close)
        quit_btn=QPushButton("Encerrar o aplicativo")
        quit_btn.setObjectName("primary")
        from PySide6.QtWidgets import QApplication
        quit_btn.clicked.connect(QApplication.instance().quit)
        l.addWidget(quit_btn)
        l.addStretch()
        return page
