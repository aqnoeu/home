"""Assistente digitável do Home: Groq para respostas, Faber offline para fala."""
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit,
    QScrollArea, QCheckBox, QFrame, QSizePolicy, QInputDialog, QMessageBox
)

from home_voice import interpret
from home_integrations import execute_windows_action
from home_groq import GroqWorker, get_key, save_key, clear_key


def typed_response(text, now=None):
    """Retorna (mensagem, ação). Somente ações do catálogo local são permitidas."""
    message = text.strip()
    if not message:
        return ("Digite uma mensagem para conversar com o Home.", None)
    s = message.casefold().strip(" !?.")
    if s in ("oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "ei home", "ei, home"):
        return ("Olá! Estou aqui. Você pode digitar comandos e ouvir minhas respostas.", None)
    if s in ("teste", "testar voz", "teste de voz", "fale comigo", "diga olá", "diga ola"):
        return ("Olá! Esta é a minha voz. Não preciso do microfone para falar com você.", None)
    if "que horas" in s or "qual é a hora" in s or "qual a hora" in s:
        time = now or datetime.now()
        return (f"Agora são {time:%H:%M}.", None)
    if "qual é a data" in s or "que dia é hoje" in s or "data de hoje" in s:
        time = now or datetime.now()
        return (f"Hoje é {time:%d/%m/%Y}.", None)
    action = interpret(message)
    if action is not None:
        return (action[1], action[0])
    return ("Por enquanto, entendo saudações, hora, data e comandos para programas, volume e música.", None)


class AssistantPage(QWidget):
    def __init__(self, home, parent=None):
        super().__init__(parent)
        self.home = home
        self.pending = None
        self.groq_worker = None
        self.setStyleSheet("""
            QWidget#assistantPage {background:transparent;color:#ececec}
            QLineEdit {background:#292b30;color:#fff;border:1px solid #53555a;border-radius:10px;padding:11px}
            QCheckBox {color:#ddd}
            QPushButton {background:#303237;color:white;border:1px solid #4c5055;border-radius:9px;padding:10px}
            QPushButton:hover {background:#44474b}
            QLabel {color:#ddd;background:transparent}
        """)
        self.setObjectName("assistantPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4,3,4,3)
        layout.setSpacing(9)
        intro=QLabel("Groq responde às perguntas • Faber fala offline • comandos locais com confirmação")
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#a5a7ab;font-size:11px")
        layout.addWidget(intro)
        self.groq_config=QPushButton("✓ Groq conectada • alterar chave" if get_key() else "Conectar Groq (uma única vez)")
        self.groq_config.clicked.connect(self.configure_groq)
        layout.addWidget(self.groq_config)
        self.messages=QScrollArea()
        self.messages.setObjectName("messagesArea")
        self.messages.setWidgetResizable(True)
        self.messages.setFrameShape(QFrame.NoFrame)
        self.messages.setMinimumHeight(160)
        self.messages.setStyleSheet("QScrollArea{background:#202125;border:1px solid #37393c;border-radius:11px}")
        self.message_host=QWidget()
        self.message_layout=QVBoxLayout(self.message_host)
        self.message_layout.setAlignment(Qt.AlignTop)
        self.message_layout.setSpacing(8)
        self.messages.setWidget(self.message_host)
        layout.addWidget(self.messages,1)

        self.confirm_box=QWidget()
        confirm_layout=QHBoxLayout(self.confirm_box)
        self.confirm_label=QLabel("")
        self.confirm_label.setWordWrap(True)
        confirm_layout.addWidget(self.confirm_label,1)
        yes=QPushButton("Autorizar")
        yes.clicked.connect(lambda:self.confirm(True))
        no=QPushButton("Cancelar")
        no.clicked.connect(lambda:self.confirm(False))
        confirm_layout.addWidget(yes)
        confirm_layout.addWidget(no)
        self.confirm_box.hide()
        layout.addWidget(self.confirm_box)

        row=QHBoxLayout()
        self.entry=QLineEdit()
        self.entry.setPlaceholderText("Digite um comando ou uma mensagem...")
        self.entry.setMaxLength(500)
        self.entry.returnPressed.connect(self.send)
        send=QPushButton("Enviar")
        send.clicked.connect(self.send)
        row.addWidget(self.entry,1)
        row.addWidget(send)
        layout.addLayout(row)

        options=QHBoxLayout()
        self.talk=QCheckBox("Responder por voz")
        self.talk.setChecked(True)
        self.talk.setToolTip("Usa a voz instalada no Windows; não requer microfone.")
        options.addWidget(self.talk)
        options.addStretch()
        self.replay=QPushButton("▶ Ouvir novamente")
        self.replay.clicked.connect(self.replay_last)
        options.addWidget(self.replay)
        layout.addLayout(options)
        self.status=QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color:#acadb0;font-size:11px")
        layout.addWidget(self.status)

        self.home.voice.state.connect(self.on_voice_state)
        for role, text in home.assistant_history[-50:]:
            self.add_bubble(role,text)
        if not home.assistant_history:
            self.record("home","Olá! Digite 'teste de voz', 'que horas são?' ou 'abra a calculadora'.")
        self.entry.setFocus()

    def add_bubble(self, role, message):
        box=QLabel(message)
        box.setWordWrap(True)
        box.setTextInteractionFlags(Qt.TextSelectableByMouse)
        user=role=="user"
        box.setStyleSheet(
            "QLabel{background:" + ("#3c424b" if user else "#2e3033")
            + ";border-radius:10px;padding:10px;color:#f1f1f1}"
        )
        line=QHBoxLayout()
        if user:line.addStretch(1)
        line.addWidget(box,0)
        if not user:line.addStretch(1)
        self.message_layout.addLayout(line)
        self.messages.verticalScrollBar().setValue(self.messages.verticalScrollBar().maximum())

    def record(self,role,message):
        self.home.assistant_history.append((role,message))
        self.home.assistant_history=self.home.assistant_history[-50:]
        self.add_bubble(role,message)

    def say(self,message):
        if self.talk.isChecked():
            self.home.voice.speak(message, force=True)

    def send(self):
        message=self.entry.text().strip()
        if not message:
            return
        if self.pending is not None:
            self.status.setText("Autorize ou cancele o comando pendente antes de enviar outro.")
            return
        self.entry.clear()
        self.record("user",message)
        response,action=typed_response(message)
        if action:
            if not self.home.integration_prefs.get("windows_controls",False):
                reply="Para executar esse comando, habilite 'Permitir controles do Windows' na página Interações."
                self.record("home",reply)
                self.say(reply)
                return
            self.pending=(action,response)
            self.confirm_label.setText("Autoriza executar: "+message+"?")
            self.confirm_box.show()
            self.record("home","Confirme a execução do comando no painel abaixo.")
            return
        # The built-in local commands and small utilities are still safe/offline.
        # All open-ended questions go to Groq; the model cannot execute actions.
        if response.startswith("Por enquanto, entendo"):
            self.ask_ai(message)
            return
        self.record("home",response)
        self.say(response)

    def configure_groq(self):
        key, accepted=QInputDialog.getText(
            self,"Conectar Groq","Cole sua chave Groq (guardada no Gerenciador de Credenciais do Windows):",
            QLineEdit.EchoMode.Password)
        if not accepted or not key.strip():
            return
        try:
            save_key(key)
            self.groq_config.setText("✓ Groq conectada • alterar chave")
            self.status.setText("Groq conectada. As respostas por voz usam a Faber local.")
        except Exception as exc:
            QMessageBox.warning(self,"Groq",str(exc)[:200])

    def ask_ai(self, question):
        if not get_key():
            self.status.setText("Conecte a Groq uma vez acima para responder perguntas abertas.")
            self.record("home","Abra Conectar Groq para ativar respostas inteligentes.")
            return
        if self.groq_worker is not None and self.groq_worker.isRunning():
            self.status.setText("O Home ainda está pensando na pergunta anterior.")
            return
        history=[{"role":"assistant" if role=="home" else "user","content":text}
                 for role,text in self.home.assistant_history[:-1]
                 if role in ("user","home")][-8:]
        worker=GroqWorker(question,history,self.home)
        self.groq_worker=worker
        self.home.groq_worker=worker
        self.status.setText("Groq está pensando…")
        worker.answered.connect(lambda answer:self.on_ai_reply(answer))
        worker.failed.connect(lambda problem:self.on_ai_error(problem))
        worker.start()

    def on_ai_reply(self,answer):
        self.record("home",answer)
        self.status.setText("Groq respondeu. Faber reproduzindo…" if self.talk.isChecked() else "Resposta pronta.")
        self.say(answer)

    def on_ai_error(self,problem):
        self.status.setText(problem)
        self.record("home","Não consegui consultar a Groq: "+problem)

    def confirm(self,allowed):
        pending=self.pending
        self.pending=None
        self.confirm_box.hide()
        if pending is None:
            return
        action,response=pending
        if not allowed:
            result="Comando cancelado."
        elif not self.home.integration_prefs.get("windows_controls",False):
            result="Permissão de controles do Windows desativada."
        else:
            try:
                execute_windows_action(action)
                result=response
            except Exception as exc:
                result="Não consegui executar o comando: "+str(exc)[:140]
        self.record("home",result)
        self.say(result)

    def replay_last(self):
        for role,message in reversed(self.home.assistant_history):
            if role=="home":
                self.home.voice.speak(message,force=True)
                return
        self.status.setText("Ainda não há resposta para reproduzir.")

    def on_voice_state(self,text):
        if text.startswith("Voz indisponível:"):
            self.status.setText(text)
        elif text=="speaking":
            self.status.setText("Reproduzindo resposta...")
        elif text and text not in ("thinking","listening") and text.startswith("Falha"):
            self.status.setText(text)
        elif not text:
            self.status.setText("")

    def disconnect_signals(self):
        try:
            self.home.voice.state.disconnect(self.on_voice_state)
        except (TypeError,RuntimeError):
            pass
