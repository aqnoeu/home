"""Home v0.7 — widget notch Windows; olhos animados, edicao e atualizador."""
import json
import math
import random
import sys
import time
from pathlib import Path
from PySide6.QtCore import Qt, QRect, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QMessageBox, QVBoxLayout,
    QFormLayout, QSpinBox, QDialog, QHBoxLayout, QGroupBox, QSizePolicy
)
from update_service import UpdateWorker, launch_update


class EyesWidget(QWidget):
    """Desenho proprio inspirado no conceito de olhos expressivos de robos."""
    MOODS = ('Normal', 'Feliz', 'Sonolento', 'Bravo')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(26)
        self.mood = 0
        self.gaze = 0.0
        self.target_gaze = 0.0
        self.next_look = time.monotonic() + 1.6
        self.next_blink = time.monotonic() + 2.5
        self.blink_begin = -1.0
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.animate)
        self.timer.start()

    def animate(self):
        now = time.monotonic()
        if now >= self.next_look:
            self.target_gaze = random.choice([-0.65, -0.35, 0.0, 0.35, 0.65])
            self.next_look = now + random.uniform(1.4, 3.7)
        self.gaze += (self.target_gaze - self.gaze) * 0.14
        if now >= self.next_blink and self.blink_begin < 0:
            self.blink_begin = now
            self.next_blink = now + random.uniform(2.3, 5.0)
        if self.blink_begin >= 0 and now - self.blink_begin > 0.30:
            self.blink_begin = -1.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if w < 20 or h < 12:
            return
        eh = min(h * 0.70, 34.0)
        ew = min(w * 0.21, eh * 0.82, 25.0)
        gap = max(7.0, ew * 0.34)
        left = w / 2 + self.gaze * min(10, w * .055) - (ew * 2 + gap) / 2
        blink = 1.0
        if self.blink_begin >= 0:
            progress = (time.monotonic() - self.blink_begin) / .30
            blink = max(.07, 1.0 - math.sin(min(1., progress) * math.pi) * .95)
        if self.mood == 2:
            blink *= .54
        height = max(2., eh * blink)
        for index in range(2):
            x = left + index * (ew + gap)
            y = (h - height) / 2
            path = QPainterPath()
            radius = min(ew * .36, height * .45, 9)
            path.addRoundedRect(x, y, ew, height, radius, radius)
            p.fillPath(path, QColor('#f2f8ff'))
            black = QColor('#05070b')
            if self.mood == 1 and blink > .6:
                p.setPen(Qt.NoPen)
                p.setBrush(black)
                p.drawEllipse(int(x-ew*.17), int(y+height*.49), int(ew*1.34), int(height*.81))
            elif self.mood == 3 and blink > .6:
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


class EditDialog(QDialog):
    def __init__(self, home):
        super().__init__(None)
        self.home = home
        self.setWindowTitle('Home — Modo Edicao')
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(330)
        self.setStyleSheet("""
            QDialog {background:#141a24;color:white}
            QLabel,QGroupBox {color:#e9eef6}
            QGroupBox {border:1px solid #374251;border-radius:8px;margin-top:9px;padding:10px}
            QGroupBox::title {subcontrol-origin:margin;left:10px;padding:0 5px}
            QSpinBox {background:#263448;color:white;border:1px solid #4b5c72;border-radius:5px;padding:5px}
            QPushButton {color:white;background:#33465d;padding:9px;border-radius:7px}
            QPushButton:hover {background:#456384}
        """)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Arraste as alcas azuis da direita e de baixo.\nAlterne entre os tamanhos recolhido e expandido.'))
        self.inputs = {}
        groups = [
            ('Recolhido', [('closed_w', 'Largura', 115, 650), ('closed_h', 'Altura', 28, 110)]),
            ('Expandido', [('open_w', 'Largura', 260, 850), ('open_h', 'Altura', 190, 650)]),
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


class Home(QWidget):
    CONFIG = Path.home() / '.home_notch.json'
    DEFAULTS = dict(offset=36,closed_w=180,closed_h=38,open_w=380,open_h=265)
    SHOULDER = 15

    def __init__(self):
        super().__init__()
        self.screen = QApplication.primaryScreen()
        self.settings = self.load_settings()
        self.expanded = False
        self.editing = False
        self.drag = None
        self.edit_dialog = None
        self.worker = None
        self.available_update = None
        self.setWindowTitle('Home v0.7')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setMouseTracking(True)
        self.eyes = EyesWidget(self)
        self.status = QLabel('●  Em espera')
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet('color:#79e3c4;background:transparent')
        self.mood_btn = QPushButton('Expressao: Normal')
        self.mood_btn.clicked.connect(self.next_mood)
        self.update_btn = QPushButton('↻  Verificar atualizacoes')
        self.update_btn.clicked.connect(self.update_clicked)
        self.edit_btn = QPushButton('✎  Editar tamanho')
        self.edit_btn.clicked.connect(self.begin_edit)
        self.quit_btn = QPushButton('Fechar Home')
        self.quit_btn.clicked.connect(QApplication.instance().quit)
        self.controls = (self.status,self.mood_btn,self.update_btn,self.edit_btn,self.quit_btn)
        for btn in (self.mood_btn,self.update_btn,self.edit_btn,self.quit_btn):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet('QPushButton{color:white;background:#253144;padding:7px;border-radius:8px} QPushButton:hover{background:#33465e}')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(27,4,27,8)
        layout.setSpacing(5)
        layout.addWidget(self.eyes)
        for item in self.controls:
            layout.addWidget(item)
            item.hide()
        self.setGeometry(self.target_rect())

    def load_settings(self):
        data = dict(self.DEFAULTS)
        try:
            old = json.loads(self.CONFIG.read_text(encoding='utf-8'))
            if isinstance(old,dict):
                for key in data:
                    value = old.get(key)
                    if isinstance(value,(int,float)) and not isinstance(value,bool):
                        data[key] = int(value)
        except (OSError,ValueError,TypeError):
            pass
        return data

    def save_settings(self):
        try:
            self.CONFIG.write_text(json.dumps(self.settings,indent=2),encoding='utf-8')
        except OSError:
            pass

    def sizes(self):
        s = self.settings
        return (s['open_w'],s['open_h']) if self.expanded else (s['closed_w'],s['closed_h'])

    def target_rect(self):
        b = self.screen.geometry()
        w,h = self.sizes()
        w,h = min(w,b.width()),min(h,b.height())
        x = max(0,min(self.settings['offset'],b.width()-w))
        return QRect(b.x()+x,b.y(),w,h)

    def apply_settings(self):
        if hasattr(self,'animation'):
            self.animation.stop()
        self.setGeometry(self.target_rect())
        self.save_settings()
        self.update()

    def change_setting(self,key,value):
        self.settings[key] = value
        self.apply_settings()
        if self.edit_dialog:
            self.edit_dialog.sync()

    def paintEvent(self,event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w,h = float(self.width()),float(self.height())
        s = float(self.SHOULDER)
        radius = min(20. if self.expanded else 13.,h/2)
        shape = QPainterPath()
        shape.moveTo(0,0)
        shape.lineTo(w,0)
        shape.cubicTo(w-s*.52,0,w-s,s*.38,w-s,s)
        shape.lineTo(w-s,h-radius)
        shape.cubicTo(w-s,h-radius*.4,w-s-radius*.4,h,w-s-radius,h)
        shape.lineTo(s+radius,h)
        shape.cubicTo(s+radius*.4,h,s,h-radius*.4,s,h-radius)
        shape.lineTo(s,s)
        shape.cubicTo(s,s*.38,s*.52,0,0,0)
        shape.closeSubpath()
        p.fillPath(shape,QColor('#05070b'))
        if self.editing:
            p.setPen(QPen(QColor('#49cbe8'),1.7,Qt.DashLine))
            p.drawPath(shape)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor('#49cbe8'))
            p.drawRoundedRect(int(w-25),int(h/2-15),7,30,3,3)
            p.drawRoundedRect(int(w/2-18),int(h-10),36,7,3,3)

    def mousePressEvent(self,event):
        p = event.position()
        if event.button() == Qt.RightButton:
            self.drag = ('move',event.globalPosition().x(),self.settings['offset'])
            event.accept()
            return
        if event.button() == Qt.LeftButton and self.editing:
            if p.x()>self.width()-31 and p.y()>self.height()-17:
                self.drag=('both',event.globalPosition(),self.sizes())
            elif p.x()>self.width()-31:
                self.drag=('width',event.globalPosition().x(),self.sizes()[0])
            elif p.y()>self.height()-17:
                self.drag=('height',event.globalPosition().y(),self.sizes()[1])
            if self.drag:
                event.accept()
                return
        if event.button()==Qt.LeftButton and p.y()<min(38,self.settings['closed_h']):
            if not self.editing:
                self.toggle()
            event.accept()
            return
        super().mousePressEvent(event)

    def resize_drag(self,kind,initial,current,start):
        key = ('open_w' if self.expanded else 'closed_w') if kind=='width' else ('open_h' if self.expanded else 'closed_h')
        bounds = {'open_w':(260,850),'closed_w':(115,650),'open_h':(190,650),'closed_h':(28,110)}
        low,high = bounds[key]
        self.change_setting(key,max(low,min(high,start+round(current-initial))))

    def mouseMoveEvent(self,event):
        if self.drag:
            kind,initial,start = self.drag
            now = event.globalPosition()
            if kind=='move':
                self.change_setting('offset',max(0,min(start+round(now.x()-initial),self.screen.geometry().width()-self.width())))
            elif kind=='both':
                self.resize_drag('width',initial.x(),now.x(),start[0])
                self.resize_drag('height',initial.y(),now.y(),start[1])
            else:
                self.resize_drag(kind,initial,now.x() if kind=='width' else now.y(),start)
            event.accept()
            return
        if self.editing:
            p=event.position()
            if p.x()>self.width()-31 and p.y()>self.height()-17: self.setCursor(Qt.SizeFDiagCursor)
            elif p.x()>self.width()-31: self.setCursor(Qt.SizeHorCursor)
            elif p.y()>self.height()-17: self.setCursor(Qt.SizeVerCursor)
            else: self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if self.drag:
            self.drag = None
            self.save_settings()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def next_mood(self):
        self.eyes.mood=(self.eyes.mood+1)%len(EyesWidget.MOODS)
        self.mood_btn.setText('Expressao: '+EyesWidget.MOODS[self.eyes.mood])
        self.eyes.update()

    def toggle(self):
        self.expanded = not self.expanded
        self.eyes.setFixedHeight(36 if self.expanded else 26)
        for item in self.controls:
            item.setVisible(self.expanded)
        if hasattr(self,'animation'):
            self.animation.stop()
        self.animation=QPropertyAnimation(self,b'geometry',self)
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.target_rect())
        self.animation.setDuration(280)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()
        if self.edit_dialog:
            self.edit_dialog.sync()

    def begin_edit(self):
        if self.editing:
            if self.edit_dialog:
                self.edit_dialog.raise_()
                self.edit_dialog.activateWindow()
            return
        self.editing=True
        self.edit_dialog=EditDialog(self)
        self.edit_dialog.finished.connect(self.end_edit)
        self.edit_dialog.show()
        self.update()

    def end_edit(self,*args):
        self.editing=False
        self.edit_dialog=None
        self.setCursor(Qt.ArrowCursor)
        self.save_settings()
        self.update()

    def update_clicked(self):
        if self.worker and self.worker.isRunning(): return
        if self.available_update:
            info=self.available_update
            answer=QMessageBox.question(self,'Atualizar Home',f"Instalar Home {info['version']}?\nO aplicativo sera reiniciado.\n\n"+info['notes'][:550],QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
            if answer!=QMessageBox.Yes: return
            self.run_worker('download',info)
        else:
            self.run_worker('check')

    def run_worker(self,action,info=None):
        self.update_btn.setEnabled(False)
        self.update_btn.setText('Consultando GitHub...' if action=='check' else 'Baixando atualizacao...')
        worker=UpdateWorker(action,info,self)
        self.worker=worker
        worker.checked.connect(self.checked)
        worker.staged.connect(self.staged)
        worker.failed.connect(self.failed)
        worker.finished.connect(lambda: self.update_btn.setEnabled(True))
        worker.start()

    def checked(self,info):
        self.available_update=info
        if info:
            self.update_btn.setText('⬇  Instalar '+info['version'])
        else:
            self.update_btn.setText('✓  Verificar atualizacoes')
            QMessageBox.information(self,'Home','Voce ja esta na versao mais recente publicada.')

    def failed(self,msg):
        self.update_btn.setText('↻  Verificar atualizacoes')
        QMessageBox.warning(self,'Atualizacao indisponivel',msg)

    def staged(self,path):
        try: launch_update(path)
        except Exception as exc:
            self.failed(str(exc))
            return
        QApplication.instance().quit()

    def closeEvent(self,event):
        self.save_settings()
        if self.edit_dialog:
            self.edit_dialog.close()
        super().closeEvent(event)


if __name__=='__main__':
    app=QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    widget=Home()
    widget.show()
    sys.exit(app.exec())
