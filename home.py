"""Home v0.7 — widget notch Windows; olhos animados, edicao e atualizador."""
import json
import ctypes
import os
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
from update_service import UpdateWorker, launch_update, VERSION
from home_ui import HomePanel
from home_navigation import Workspace
from home_integrations import load_preferences, save_preferences, ChromeBridge, IntegrationsDialog
from home_voice import VoiceManager, VoiceDialog


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
            progress = (time.monotonic() - self.blink_begin) / self.blink_duration
            blink = max(.07, 1.0 - math.sin(min(1., progress) * math.pi) * .95)
        if self.mood == 2:
            blink *= .54
        if self.voice_state == 'listening':
            height_factor = 1.08
        elif self.voice_state == 'thinking':
            height_factor = 0.72
        elif self.voice_state == 'speaking':
            height_factor = 0.86 + 0.14 * math.sin(time.monotonic() * 13)
        else:
            height_factor = 1.0
        blink *= height_factor
        height = max(2., eh * blink)
        for index in range(2):
            x = left + index * (ew + gap)
            y = (h - height) / 2 + self.gaze_y * min(4.,h*.12)
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
            QDialog {background:#191a1c;color:white}
            QLabel,QGroupBox {color:#e9eef6}
            QGroupBox {border:1px solid #374251;border-radius:8px;margin-top:9px;padding:10px}
            QGroupBox::title {subcontrol-origin:margin;left:10px;padding:0 5px}
            QSpinBox {background:#263448;color:white;border:1px solid #4b5c72;border-radius:5px;padding:5px}
            QPushButton {color:white;background:#33465d;padding:9px;border-radius:7px}
            QPushButton:hover {background:#456384}
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


class Home(QWidget):
    CONFIG = Path.home() / '.home_notch.json'
    DEFAULTS = dict(offset=36,closed_w=180,closed_h=22,open_w=520,open_h=350)
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
        self.integration_prefs = load_preferences()
        self.chrome_bridge = ChromeBridge(self.integration_prefs)
        self.last_page = None
        self.assistant_history = []
        self.chrome_bridge.received.connect(self._remember_page)
        self.eyes_dialog = None
        # Detecta clique externo mesmo quando outro programa recebe o foco.
        self._outside_timer = QTimer(self)
        self._outside_timer.setInterval(45)
        self._outside_timer.timeout.connect(self._watch_outside_click)
        self._mouse_was_down = False
        self._outside_timer.start()
        self.setWindowTitle(f'Home v{VERSION}')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setMouseTracking(True)
        self.eyes = EyesWidget(self)
        self.eyes.follow_mouse = self.integration_prefs['eyes_follow_mouse']
        self.eyes.react_clicks = self.integration_prefs['eyes_react_clicks']
        self.voice = VoiceManager(self)
        self.voice.confirmation_requested.connect(self.on_voice_confirmation)
        self.panel = HomePanel(self)
        self.panel.hide()
        self.page = "hub"
        self.workspace = Workspace(self, self)
        self.workspace.hide()
        self.workspace.requested.connect(self.navigate)
        self.panel.mood_changed.connect(self.set_mood)
        self.panel.more.clicked.connect(self.next_mood)
        self.update_btn = self.panel.update_btn
        self.edit_btn = self.panel.edit_btn
        self.quit_btn = self.panel.quit_btn
        self.voice_btn = self.panel.voice_btn
        self.voice_btn.clicked.connect(lambda:self.navigate('voice'))
        self.panel.assistant_btn.clicked.connect(lambda:self.navigate('assistant'))
        self.voice.state.connect(self.on_voice_status)
        self.on_voice_status("")
        self.interactions_btn = self.panel.interactions_btn
        self.interactions_btn.clicked.connect(lambda:self.navigate('integrations'))
        self.update_btn.clicked.connect(lambda:self.navigate('updates'))
        self.edit_btn.clicked.connect(lambda:self.navigate('edit'))
        self.quit_btn.clicked.connect(lambda:self.navigate('exit'))
        self.eyes.setFixedHeight(self.settings['closed_h'])
        self.setGeometry(self.target_rect())
        self.position_children()
        try:
            self.chrome_bridge.start()
        except OSError:
            pass  # Porta local indisponivel; a interface ainda funciona.
        if self.integration_prefs.get('voice_microphone') and self.integration_prefs.get('voice_wake'):
            self.voice.start('wake')
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def _remember_page(self,title,url,content):
        self.last_page = (title,url,content)

    def on_voice_status(self, status):
        if not self.integration_prefs.get('voice_microphone'):
            self.panel.mic_status.setText("")
        elif status == "listening":
            self.panel.mic_status.setText("● MIC  ")
        elif status == "speaking":
            self.panel.mic_status.setText("◉ FALA  ")
        elif status == "thinking":
            self.panel.mic_status.setText("…  ")
        elif self.integration_prefs.get('voice_wake'):
            self.panel.mic_status.setText("● EI HOME  ")
        else:
            self.panel.mic_status.setText("")
        self.panel.mic_status.setToolTip(status or "Microfone em espera")

    def on_voice_confirmation(self, phrase, action):
        if self.page != 'voice' or not self.expanded:
            self.navigate('voice')

    def navigate(self, section):
        if section == 'hub':
            self.editing = False
            self.page = 'hub'
            self.workspace.set_section('hub')
            self.workspace.hide()
            self.panel.setVisible(self.expanded)
            self.eyes.follow_mouse = self.integration_prefs['eyes_follow_mouse']
            self.eyes.react_clicks = self.integration_prefs['eyes_react_clicks']
            self.on_voice_status("")
        else:
            self.expanded = True
            self.page = section
            self.editing = section == 'edit'
            self.panel.hide()
            self.workspace.set_section(section)
            self.workspace.show()
        self.animate_to_target()

    def collapse(self):
        if not self.expanded:
            return
        self.expanded=False
        self.editing=False
        self.page='hub'
        self.workspace.set_section('hub')
        self.workspace.hide()
        self.panel.hide()
        self.animate_to_target()

    def animate_to_target(self):
        if hasattr(self,'animation'):
            self.animation.stop()
        self.animation=QPropertyAnimation(self,b'geometry',self)
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.target_rect())
        self.animation.setDuration(280)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()
        self.position_children()
        if self.edit_dialog:
            self.edit_dialog.sync()

    def open_voice(self):
        self.navigate('voice')

    def open_integrations(self):
        self.navigate('integrations')

    def _watch_outside_click(self):
        if os.name != 'nt':
            return
        left_down = bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
        right_down = bool(ctypes.windll.user32.GetAsyncKeyState(0x02) & 0x8000)
        down = left_down or right_down
        new_click = down and not self._mouse_was_down
        self._mouse_was_down = down
        if new_click and getattr(self,'eyes',None) and self.eyes.react_clicks:
            self.eyes.blink_on_click()
        if not new_click or not self.expanded or self.editing or self.drag:
            return
        # Nao fecha durante confirmacoes de atualizacao e caixas de aviso.
        if QApplication.activeModalWidget() is not None:
            return
        from PySide6.QtGui import QCursor
        cursor_pos = QCursor.pos()
        if not self.geometry().contains(cursor_pos):
            self.toggle()

    def position_children(self):
        if self.expanded:
            eye_h = min(38, max(24, self.height() // 9))
            panel_y = min(77, max(52, int(self.height() * .22)))
            self.eyes.setFixedHeight(eye_h)
            self.eyes.setGeometry(24, 3, max(30, self.width()-48), eye_h)
            self.panel.setGeometry(15, panel_y, max(1,self.width()-30), max(1,self.height()-panel_y-5))
            self.workspace.setGeometry(15, panel_y, max(1,self.width()-30), max(1,self.height()-panel_y-5))
        else:
            eye_h = self.settings['closed_h']
            self.eyes.setFixedHeight(eye_h)
            self.eyes.setGeometry(17, 0, max(30,self.width()-34), eye_h)
        self.eyes.raise_()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'panel'):
            self.position_children()

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
        if self.expanded and self.page != 'hub':
            w,h = 690,610
        w,h = min(w,b.width()),min(h,b.height())
        x = max(0,min(self.settings['offset'],b.width()-w))
        return QRect(b.x()+x,b.y(),w,h)

    def apply_settings(self):
        if hasattr(self,'animation'):
            self.animation.stop()
        if not self.expanded:
            self.eyes.setFixedHeight(self.settings['closed_h'])
        self.setGeometry(self.target_rect())
        self.position_children()
        self.save_settings()
        self.update()

    def change_setting(self,key,value):
        self.settings[key] = value
        if key == 'closed_h' and not self.expanded:
            self.eyes.setFixedHeight(value)
        self.apply_settings()
        if self.edit_dialog:
            self.edit_dialog.sync()
        if self.page == 'edit' and hasattr(self.workspace.current, 'sync'):
            self.workspace.current.sync()

    def paintEvent(self,event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w,h = float(self.width()),float(self.height())
        s = min(float(self.SHOULDER), h * .43)
        radius = min(20. if self.expanded else 13.,h*.48)
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
        p.fillPath(shape,QColor('#060607'))
        if self.editing:
            p.setPen(QPen(QColor('#8d8e90'),1.7,Qt.DashLine))
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
        bounds = {'open_w':(380,850),'closed_w':(115,650),'open_h':(265,650),'closed_h':(18,110)}
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

    def set_mood(self,index):
        self.eyes.mood = {0:0,1:1,2:3}.get(index,0)
        self.panel.set_mood(index)
        self.eyes.update()

    def next_mood(self):
        self.eyes.mood = (self.eyes.mood+1) % len(EyesWidget.MOODS)
        index={0:0,1:1,3:2}.get(self.eyes.mood,-1)
        self.panel.set_mood(index)
        self.eyes.update()

    def toggle(self):
        if self.expanded:
            self.collapse()
            return
        self.expanded=True
        self.page='hub'
        self.panel.show()
        self.workspace.hide()
        self.animate_to_target()

    def begin_edit(self):
        self.navigate('edit')

    def end_edit(self,*args):
        self.editing=False
        self.panel.setAttribute(Qt.WA_TransparentForMouseEvents, False)
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
        if self.page == 'updates':
            self.workspace.update_result(info)
        if info:
            self.update_btn.setText('⬇  Instalar '+info['version'])
        else:
            self.update_btn.setText('✓  Verificar atualizacoes')
            if self.page != 'updates':
                QMessageBox.information(self,'Home','Voce ja esta na versao mais recente publicada.')

    def failed(self,msg):
        self.update_btn.setText('↻  Verificar atualizacoes')
        if self.page == 'updates':
            self.workspace.update_failed(msg)
        else:
            QMessageBox.warning(self,'Atualizacao indisponivel',msg)

    def staged(self,path):
        try: launch_update(path)
        except Exception as exc:
            self.failed(str(exc))
            return
        QApplication.instance().quit()

    def shutdown(self):
        self.voice.stop()
        if self.voice.worker and self.voice.worker.isRunning():
            self.voice.worker.wait(2500)
        if self.voice.speaker and self.voice.speaker.isRunning():
            self.voice.speaker.wait(6000)
        if self.voice.kokoro_download_worker and self.voice.kokoro_download_worker.isRunning():
            self.voice.kokoro_download_worker.requestInterruption()
            self.voice.kokoro_download_worker.wait(65000)
        for worker in list(self.voice.voice_list_workers):
            if worker.isRunning():
                worker.wait(6000)
        self.chrome_bridge.stop()
        self.save_settings()

    def closeEvent(self,event):
        self.shutdown()
        if self.edit_dialog:
            self.edit_dialog.close()
        super().closeEvent(event)


if __name__=='__main__':
    app=QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    widget=Home()
    widget.show()
    sys.exit(app.exec())
