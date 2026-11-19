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
from home_integrations import load_preferences, save_preferences, ChromeBridge, IntegrationsDialog, cleanup_retired_voice
from home_voice import VoiceManager, VoiceDialog
from home_chat_store import ChatStore
from home_emotions import ContextState, WindowsContext, normalize_emotion
from home_eyes import EyesWidget  # retained public import for existing integrations
from home_edit_dialog import EditDialog



class Home(QWidget):
    CONFIG = Path.home() / '.home_notch.json'
    DEFAULTS = dict(offset=36,closed_w=180,closed_h=22,open_w=520,open_h=350,eye_gap=9)
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
        cleanup_retired_voice()
        self.chrome_bridge = ChromeBridge(self.integration_prefs)
        self.last_page = None
        self.chat_store = ChatStore()
        self.assistant_history = [(x["role"],x["text"]) for x in self.chat_store.messages()]
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
        self.emotion_context = ContextState()
        self._context_timer = QTimer(self)
        self._context_timer.setInterval(4000)
        self._context_timer.timeout.connect(self._refresh_emotion_context)
        self._context_timer.start()
        self.eyes = EyesWidget(self)
        self._manual_expression_until = 0.0
        self.apply_saved_expression()
        self.eyes.eye_gap = self.settings["eye_gap"]
        self.eyes.follow_mouse = self.integration_prefs['eyes_follow_mouse']
        self.eyes.react_clicks = self.integration_prefs['eyes_react_clicks']
        self.voice = VoiceManager(self)
        self.voice.confirmation_requested.connect(self.on_voice_confirmation)
        self.voice.wake_detected.connect(self.on_voice_wake)
        self.panel = HomePanel(self)
        self.panel.hide()
        self.page = "hub"
        self.workspace = Workspace(self, self)
        self.workspace.hide()
        self.workspace.requested.connect(self.navigate)
        self.panel.mood_changed.connect(self.set_mood)
        self.panel.more.clicked.connect(lambda: self.navigate("expressions"))
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

    def record_chat(self, role, message, session=None):
        self.chat_store.add(role, message, id=session)
        if session is None or session == self.chat_store.active():
            self.assistant_history = [(x["role"],x["text"]) for x in self.chat_store.messages()]

    def select_chat(self, id):
        self.chat_store.select(id)
        self.assistant_history = [(x["role"],x["text"]) for x in self.chat_store.messages()]

    def set_ai_emotion(self, emotion):
        self.emotion_context.note_conversation(normalize_emotion(emotion))
        if not self.manual_expression_active():
            self.eyes.emotion = normalize_emotion(emotion)

    def _refresh_emotion_context(self):
        now = time.monotonic()
        activity, foreground, charging = WindowsContext.sample(now)
        self.emotion_context.last_activity = activity
        if foreground != self.emotion_context.focused_window:
            self.emotion_context.focused_window = foreground
            self.emotion_context.focused_since = now
        low, saver = WindowsContext.power_details()
        if self.manual_expression_active():
            self.apply_saved_expression()
        else:
            self.eyes.mood = 0
            self.eyes.emotion = self.emotion_context.choose(
                now, charging=charging, battery_low=low, power_saver=saver)

    def _remember_page(self,title,url,content):
        self.last_page = (title,url,content)

    def on_voice_status(self, status):
        if hasattr(self, "eyes"):
            self.eyes.voice_state = status if status in ("listening", "thinking", "speaking") else ""
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

    def on_voice_wake(self):
        # Ok/Ei Home abre a caixa de conversa para mostrar a pergunta e a resposta.
        if self.page not in ('assistant', 'voice') or not self.expanded:
            self.navigate('assistant')

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
                # Manual selection is intentionally temporary, never restored after restart.
                data["expression_fixed"] = False
                selected = old.get("selected_expression", 0)
                data["selected_expression"] = selected if type(selected) is int and 0 <= selected < 12 else 0
                hidden = old.get("hidden_expressions", [])
                data["hidden_expressions"] = sorted(set(x for x in hidden if type(x) is int and 0 <= x < 12)) if isinstance(hidden, list) else []
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
        if hasattr(self, "eyes"):
            self.eyes.eye_gap = max(0, min(600, self.settings.get("eye_gap",9)))
            self.eyes.update()
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

    def manual_expression_active(self):
        if not self.settings.get("expression_fixed", False):
            return False
        if time.monotonic() < self._manual_expression_until:
            return True
        self.settings["expression_fixed"] = False
        self.eyes.preview_emotion = None
        self.eyes.mood = 0
        return False

    def apply_saved_expression(self):
        """Apply a fixed catalog face to the real notch, without a 12s timeout."""
        if not self.settings.get("expression_fixed", False):
            return
        from home_expression_gallery import EXPRESSIONS
        index = self.settings.get("selected_expression", 0)
        hidden = self.settings.get("hidden_expressions", [])
        if index in hidden or not 0 <= index < len(EXPRESSIONS):
            index = next((i for i in range(len(EXPRESSIONS)) if i not in hidden), 0)
            self.settings["selected_expression"] = index
        _, emotion, mood = EXPRESSIONS[index]
        self.eyes.mood = mood
        self.eyes.preview_emotion = None
        self.eyes.emotion = emotion
        if emotion in EyesWidget.EXTRA_EXPRESSIONS:
            self.eyes.preview_emotion = emotion
            self.eyes.preview_until = float("inf")
        self.eyes.update()

    def select_expression(self, index):
        from home_expression_gallery import EXPRESSIONS
        if not 0 <= index < len(EXPRESSIONS) or index in self.settings.get("hidden_expressions", []):
            return False
        self.settings["selected_expression"] = index
        self.settings["expression_fixed"] = True
        self._manual_expression_until = time.monotonic() + 30.0
        self.apply_saved_expression()
        self.save_settings()
        return True

    def use_automatic_expressions(self):
        self.settings["expression_fixed"] = False
        self._manual_expression_until = 0.0
        self.eyes.preview_emotion = None
        self.eyes.mood = 0
        self._refresh_emotion_context()
        self.save_settings()

    def set_expression_visible(self, index, visible):
        hidden = set(self.settings.get("hidden_expressions", []))
        if visible:
            hidden.discard(index)
        else:
            if len(hidden) >= 11:
                return False
            hidden.add(index)
        self.settings["hidden_expressions"] = sorted(hidden)
        if self.settings.get("expression_fixed", False):
            self.apply_saved_expression()
        self.save_settings()
        return True

    def set_mood(self,index):
        # Legacy hub controls share the persisted expression selection.
        catalog_index = {0:0,1:1,2:3}.get(index,0)
        if catalog_index in self.settings.get("hidden_expressions", []):
            return
        self.select_expression(catalog_index)
        self.panel.set_mood(index)

    def next_mood(self):
        # Alterna as oito novas expressoes com previa de 12 segundos.
        current = getattr(self, "_extra_mood_index", -1)
        self._extra_mood_index = (current + 1) % len(EyesWidget.EXTRA_EXPRESSIONS)
        self.eyes.mood = 0
        self.eyes.show_expression(EyesWidget.EXTRA_EXPRESSIONS[self._extra_mood_index])
        self.panel.set_mood(-1)
        self.panel.more.setToolTip("Expressao: " + EyesWidget.EXTRA_EXPRESSIONS[self._extra_mood_index])

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
        if self.voice.faber_download_worker and self.voice.faber_download_worker.isRunning():
            self.voice.faber_download_worker.requestInterruption()
            self.voice.faber_download_worker.wait(65000)
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
