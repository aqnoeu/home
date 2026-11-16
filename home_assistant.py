"""Assistente digitável do Home: Groq para respostas, Faber offline para fala."""
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit,
    QScrollArea, QCheckBox, QFrame, QSizePolicy, QComboBox
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
    return ("Posso informar hora e data e, com autorização, abrir programas, Gerenciador de Tarefas, Painel de Controle e controlar a mídia.", None)


class AssistantPage(QWidget):
    def __init__(self, home, parent=None):
        super().__init__(parent)
        self.home = home
        self.pending = None
        self.groq_worker = None
        self.setStyleSheet("""
            QWidget#assistantPage {background:transparent;color:#FFFFFF}
            QLineEdit {background:#1C2737;color:#fff;border:1px solid #324357;border-radius:10px;padding:11px}
            QCheckBox {color:#DDE7F4}
            QPushButton {background:#1C2737;color:white;border:1px solid #324357;border-radius:9px;padding:10px}
            QPushButton:hover {background:#26384F}
            QLabel {color:#DDE7F4;background:transparent}
        """)
        self.setObjectName("assistantPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10,12,10,12)
        layout.setSpacing(12)
        intro=QLabel("Converse com o HOME. A Groq responde; a Faber dá voz às mensagens.")
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#A8B6C8;font-size:12px")
        layout.addWidget(intro)
        self.groq_config=QPushButton("Groq configurada · Gerenciar" if get_key() else "Conectar Groq")
        self.groq_config.clicked.connect(self.configure_groq)
        layout.addWidget(self.groq_config)
        # Inline credential panel: never open a modal behind HOME's always-on-top notch.
        self.groq_panel=QFrame(self)
        self.groq_panel.setObjectName("groqCredentialPanel")
        self.groq_panel.setStyleSheet("""
            QFrame#groqCredentialPanel {background:#141D2A;border:1px solid #324357;border-radius:13px}
            QLineEdit {background:#1C2737;border:1px solid #324357;border-radius:9px;
                       color:white;padding:10px}
            QPushButton#saveGroq {background:#2F6BFF;color:#FFFFFF;border:1px solid #2F6BFF;
                                  border-radius:9px;padding:11px;font-weight:600}
        """)
        credential_layout=QVBoxLayout(self.groq_panel)
        credential_layout.setContentsMargins(14,13,14,13)
        credential_layout.setSpacing(9)
        self.groq_hint=QLabel("Cole sua chave Groq. Ela será guardada no Gerenciador de Credenciais do Windows.")
        self.groq_hint.setWordWrap(True)
        credential_layout.addWidget(self.groq_hint)
        self.groq_input=QLineEdit()
        self.groq_input.setObjectName("groqKeyInput")
        self.groq_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_input.setPlaceholderText("gsk_...")
        self.groq_input.returnPressed.connect(self.save_groq_inline)
        credential_layout.addWidget(self.groq_input)
        key_actions=QHBoxLayout()
        save=QPushButton("Salvar conexão")
        save.setObjectName("saveGroq")
        save.clicked.connect(self.save_groq_inline)
        test=QPushButton("Testar Groq")
        test.setObjectName("testGroq")
        test.clicked.connect(self.test_groq_inline)
        cancel=QPushButton("Cancelar")
        cancel.clicked.connect(self.hide_groq_inline)
        disconnect=QPushButton("Desconectar")
        disconnect.clicked.connect(self.disconnect_groq_inline)
        key_actions.addWidget(save)
        key_actions.addWidget(test)
        key_actions.addWidget(disconnect)
        key_actions.addWidget(cancel)
        credential_layout.addLayout(key_actions)
        self.groq_panel.setVisible(False)
        layout.addWidget(self.groq_panel)
        # Chat history controls stay within HOME: no popups.
        chats=QHBoxLayout()
        self.chat_selector=QComboBox(self)
        self.chat_selector.setObjectName("savedChats")
        self.chat_selector.setStyleSheet("QComboBox{background:#1C2737;color:white;border:1px solid #324357;border-radius:9px;padding:9px}")
        self.chat_selector.currentIndexChanged.connect(self.select_chat)
        chats.addWidget(self.chat_selector,1)
        new_chat_button=QPushButton("+ Nova")
        new_chat_button.clicked.connect(self.new_chat)
        chats.addWidget(new_chat_button)
        self.delete_chat_btn=QPushButton("Excluir")
        self.delete_chat_btn.clicked.connect(self.delete_chat)
        chats.addWidget(self.delete_chat_btn)
        layout.addLayout(chats)
        self.pending_chat_delete=False
        self.refresh_chat_selector()
        self.messages=QScrollArea()
        self.messages.setObjectName("messagesArea")
        self.messages.setWidgetResizable(True)
        self.messages.setFrameShape(QFrame.NoFrame)
        self.messages.setMinimumHeight(135)
        self.messages.setStyleSheet("QScrollArea{background:#141D2A;border:1px solid #324357;border-radius:11px}")
        self.message_host=QWidget()
        self.message_layout=QVBoxLayout(self.message_host)
        self.message_layout.setAlignment(Qt.AlignTop)
        self.message_layout.setSpacing(10)
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
        row.setSpacing(9)
        self.entry=QLineEdit()
        self.entry.setPlaceholderText("Digite um comando ou uma mensagem...")
        self.entry.setMaxLength(500)
        self.entry.returnPressed.connect(self.send)
        send=QPushButton("Enviar")
        send.setObjectName("sendPrimary")
        send.clicked.connect(self.send)
        microphone=QPushButton("🎙 Falar")
        microphone.setToolTip("Usar o microfone do Windows para conversar com HOME")
        microphone.clicked.connect(self.home.voice.toggle_push)
        row.addWidget(microphone)
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
        self.status.setStyleSheet("color:#A8B6C8;font-size:11px")
        layout.addWidget(self.status)

        self.home.voice.state.connect(self.on_voice_state)
        self.home.voice.command.connect(self.on_voice_command)
        for role, text in home.assistant_history[-50:]:
            self.add_bubble(role,text)
        if not home.assistant_history:
            self.add_bubble("home","Olá! Você pode começar uma conversa ou abrir uma anterior.")
        self.entry.setFocus()

    def add_bubble(self, role, message):
        box=QLabel(message)
        box.setWordWrap(True)
        box.setTextInteractionFlags(Qt.TextSelectableByMouse)
        user=role=="user"
        box.setStyleSheet(
            "QLabel{background:" + ("#3c424b" if user else "#1C2737")
            + ";border-radius:10px;padding:10px;color:#f1f1f1}"
        )
        line=QHBoxLayout()
        if user:line.addStretch(1)
        line.addWidget(box,0)
        if not user:line.addStretch(1)
        self.message_layout.addLayout(line)
        self.messages.verticalScrollBar().setValue(self.messages.verticalScrollBar().maximum())

    def record(self,role,message):
        self.home.record_chat(role,message)
        self.add_bubble(role,message)
        self.refresh_chat_selector()

    def refresh_chat_selector(self):
        selected=self.home.chat_store.active()
        self.chat_selector.blockSignals(True)
        self.chat_selector.clear()
        for item in self.home.chat_store.all():
            self.chat_selector.addItem(item["title"][:45],item["id"])
        index=self.chat_selector.findData(selected)
        if index>=0:self.chat_selector.setCurrentIndex(index)
        self.chat_selector.blockSignals(False)

    def load_chat_messages(self):
        self.message_host=QWidget()
        self.message_layout=QVBoxLayout(self.message_host)
        self.message_layout.setAlignment(Qt.AlignTop)
        self.message_layout.setSpacing(10)
        self.messages.setWidget(self.message_host)
        for role,message in self.home.assistant_history:
            self.add_bubble(role,message)
        if not self.home.assistant_history:
            self.add_bubble("home","Escreva uma mensagem para começar esta conversa.")

    def select_chat(self,index):
        if index<0:return
        target=self.chat_selector.itemData(index)
        if not target or target==self.home.chat_store.active():return
        self.home.select_chat(target)
        self.pending_chat_delete=False
        self.delete_chat_btn.setText("Excluir")
        if hasattr(self,"messages"):
            self.load_chat_messages()

    def new_chat(self):
        self.home.chat_store.new()
        self.home.assistant_history=[]
        self.pending_chat_delete=False
        self.delete_chat_btn.setText("Excluir")
        self.refresh_chat_selector()
        self.load_chat_messages()
        self.status.setText("Nova conversa criada. Histórico anterior preservado.")

    def delete_chat(self):
        if not self.pending_chat_delete:
            self.pending_chat_delete=True
            self.delete_chat_btn.setText("Confirmar exclusão")
            self.status.setText("Clique novamente para excluir permanentemente esta conversa.")
            return
        self.home.chat_store.delete(self.home.chat_store.active())
        self.home.chat_store.new()
        self.home.assistant_history=[]
        self.pending_chat_delete=False
        self.delete_chat_btn.setText("Excluir")
        self.refresh_chat_selector()
        self.load_chat_messages()
        self.status.setText("Conversa excluída deste computador.")

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
        if response.startswith("Posso informar hora e data"):
            self.ask_ai(message)
            return
        self.record("home",response)
        self.say(response)

    def configure_groq(self):
        """Expand the in-page field instead of opening QInputDialog behind HOME."""
        self.groq_panel.setVisible(not self.groq_panel.isVisible())
        if self.groq_panel.isVisible():
            self.groq_input.setFocus()

    def hide_groq_inline(self):
        self.groq_input.clear()
        self.groq_panel.hide()

    def disconnect_groq_inline(self):
        try:
            clear_key()
            self.groq_input.clear()
            self.groq_config.setText("Conectar Groq")
            self.groq_hint.setText("Conexão removida deste PC. As conversas foram preservadas.")
            self.status.setText("Groq desconectada. Seu histórico continua salvo.")
        except Exception as exc:
            self.groq_hint.setText("Falha ao desconectar: "+str(exc)[:160])

    def save_groq_inline(self):
        try:
            save_key(self.groq_input.text())
            self.groq_config.setText("Groq configurada · Gerenciar")
            self.groq_hint.setText("Chave salva e recuperada no Windows. Use Testar Groq para validar a autenticação.")
            self.status.setText("Chave guardada e verificada localmente. A autenticação com Groq ainda não foi testada.")
            self.hide_groq_inline()
        except Exception as exc:
            self.groq_hint.setText("Não foi possível salvar: "+str(exc)[:160])

    def test_groq_inline(self):
        # Real authentication check without a popup, plaintext logs, or audio.
        if self.groq_input.text().strip():
            try:
                save_key(self.groq_input.text())
                self.groq_input.clear()
            except Exception as exc:
                self.groq_hint.setText("Chave inválida: "+str(exc)[:160])
                return
        if not get_key():
            self.groq_hint.setText("Cole sua chave Groq antes de testar.")
            return
        if self.groq_worker and self.groq_worker.isRunning():
            self.groq_hint.setText("Já estou verificando a conexão.")
            return
        worker=GroqWorker("Responda apenas com uma saudação curta.", parent=self.home, check_credentials=True)
        self.groq_worker=worker
        self.home.groq_worker=worker
        self.groq_hint.setText("Verificando conexão e permissão do modelo…")
        worker.credentials_checked.connect(lambda available:self.groq_hint.setText(
            "Chave autenticada. Verificando resposta do modelo…" if available
            else "Chave autenticada, mas modelo indisponível."))
        worker.answered.connect(lambda text:self.groq_hint.setText(
            "✓ Autenticação aprovada. Groq funcionando neste PC: "+text[:90]))
        worker.failed.connect(lambda problem:self.groq_hint.setText(
            "Teste falhou: "+problem[:180]))
        worker.start()

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
        worker.chat_id=self.home.chat_store.active()
        self.groq_worker=worker
        self.home.groq_worker=worker
        self.status.setText("Groq está pensando…")
        worker.emotional_answer.connect(lambda _text, emotion:self.home.set_ai_emotion(emotion))
        worker.answered.connect(lambda answer:self.on_ai_reply(worker,answer))
        worker.failed.connect(lambda problem:self.on_ai_error(worker,problem))
        worker.start()

    def on_ai_reply(self,worker,answer):
        self.home.record_chat("home",answer,session=worker.chat_id)
        if worker.chat_id == self.home.chat_store.active():
            self.add_bubble("home",answer)
            self.refresh_chat_selector()
            self.status.setText("Groq respondeu.")
            self.say(answer)

    def on_ai_error(self,worker,problem):
        if worker.chat_id == self.home.chat_store.active():
            self.status.setText(problem)
            self.add_bubble("home","Não consegui consultar a Groq: "+problem)

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

    def on_voice_command(self,phrase):
        # The voice manager persists the transcript immediately after emitting command.
        QTimer.singleShot(0, self.load_chat_messages)

    def on_voice_state(self,text):
        if text == "speaking":
            QTimer.singleShot(0, self.load_chat_messages)
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
        try:
            self.home.voice.command.disconnect(self.on_voice_command)
        except (TypeError,RuntimeError):
            pass
