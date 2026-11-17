"""HOME Windows: conta unificada Supabase + dispositivos, sem comprometer recursos offline."""
import json
import uuid
import socket
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
import keyring
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Qt
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QListWidget

BASE="https://homehub-ia.vercel.app"
SERVICE="home-unified-account"
CLIENT_FILE=Path.home()/".home_client_id"
def request(url, method="GET", data=None, headers=None):
    h={"Accept":"application/json",**(headers or {})}
    if data is not None:
        data=json.dumps(data).encode("utf-8")
        h["Content-Type"]="application/json"
    req=Request(url,data=data,headers=h,method=method)
    try:
        with urlopen(req,timeout=15) as response:
            raw=response.read()
            return json.loads(raw) if raw else {}
    except Exception as e:
        if hasattr(e,"read"):
            try:
                msg=json.loads(e.read()).get("error_description") or "Operação recusada."
                raise RuntimeError(msg) from None
            except (ValueError,AttributeError):
                pass
        raise RuntimeError("Acesso à conta indisponível: "+str(e)) from None

class AccountClient:
    def __init__(self):
        conf=request(BASE+"/api/config")
        self.url=conf["supabaseUrl"].rstrip("/")
        self.key=conf["supabasePublishableKey"]
        self.access=None
        self.uid=None
        self.email=None
        if CLIENT_FILE.exists():
            self.device=CLIENT_FILE.read_text(encoding="utf-8").strip()
        else:
            self.device=str(uuid.uuid4())
            CLIENT_FILE.write_text(self.device,encoding="utf-8")
    def auth_headers(self):
        return {"apikey":self.key,"Authorization":"Bearer "+self.access}
    def token(self,grant,values):
        result=request(self.url+"/auth/v1/token?grant_type="+grant,"POST",values,{"apikey":self.key})
        self.access=result["access_token"]
        user=result.get("user") or {}
        self.uid=user.get("id")
        self.email=user.get("email")
        if result.get("refresh_token"):keyring.set_password(SERVICE,"refresh",result["refresh_token"])
        self.register()
        return self.email
    def login(self,email,password):
        return self.token("password",{"email":email,"password":password})
    def resume(self):
        refresh=keyring.get_password(SERVICE,"refresh")
        if refresh:return self.token("refresh_token",{"refresh_token":refresh})
        return None
    def register(self):
        if not self.uid:return
        request(self.url+"/rest/v1/home_devices?on_conflict=user_id,client_id","POST",
            {"user_id":self.uid,"client_id":self.device,"display_name":socket.gethostname()[:80],"platform":"windows"},
            {**self.auth_headers(),"Prefer":"resolution=merge-duplicates"})
    def get_preferences(self):
        rows=request(self.url+"/rest/v1/home_preferences?select=*&user_id=eq."+quote(self.uid),"GET",headers=self.auth_headers())
        return rows[0] if rows else {}
    def save_preferences(self,model,style,sync):
        request(self.url+"/rest/v1/home_preferences?on_conflict=user_id","POST",{
            "user_id":self.uid,"preferred_model":model,"response_style":style,"sync_chats":sync
        },{**self.auth_headers(),"Prefer":"resolution=merge-duplicates"})
    def chats(self):
        return request(self.url+"/rest/v1/homehub_chats?select=id,title,updated_at&order=updated_at.desc&limit=40",
                       headers=self.auth_headers())
    def messages(self, chat_id):
        return request(self.url+"/rest/v1/homehub_messages?select=role,content&chat_id=eq."+quote(chat_id)+"&order=created_at.asc&limit=150",headers=self.auth_headers())
    def upload_local(self, store):
        if not self.get_preferences().get("sync_chats",False):
            raise RuntimeError("Ative a sincronização no HOME HUB antes de enviar conversas locais.")
        data=store.data.get("chats",[])
        chats=[];messages=[]
        for chat in data:
            try:uuid.UUID(chat["id"])
            except (ValueError,TypeError,KeyError):continue
            cid=chat["id"]
            chats.append({"id":cid,"user_id":self.uid,"title":str(chat.get("title","Conversa"))[:120],"model":"auto"})
            for i,message in enumerate(chat.get("messages",[])):
                role=message.get("role")
                if role not in ("user","home"):continue
                content=str(message.get("text","")).strip()
                if not content:continue
                mid=str(uuid.uuid5(uuid.NAMESPACE_URL,"home-windows:"+cid+":"+str(i)))
                messages.append({"id":mid,"chat_id":cid,"user_id":self.uid,"role":"assistant" if role=="home" else "user","content":content})
        if chats:request(self.url+"/rest/v1/homehub_chats?on_conflict=id","POST",chats,{**self.auth_headers(),"Prefer":"resolution=merge-duplicates"})
        for start in range(0,len(messages),80):
            request(self.url+"/rest/v1/homehub_messages?on_conflict=id","POST",messages[start:start+80],{**self.auth_headers(),"Prefer":"resolution=ignore-duplicates"})
        return len(messages)
    def logout(self):
        try:request(self.url+"/auth/v1/logout","POST",{},self.auth_headers())
        finally:
            try:keyring.delete_password(SERVICE,"refresh")
            except Exception:pass
            self.access=None;self.uid=None;self.email=None
class TaskSignals(QObject):
    done=Signal(object)
    failed=Signal(str)
class Task(QRunnable):
    def __init__(self,work):
        super().__init__();self.work=work;self.signals=TaskSignals()
    def run(self):
        try:self.signals.done.emit(self.work())
        except Exception as e:self.signals.failed.emit(str(e))
class AccountPage(QWidget):
    """Tela interna ao notch; rede sempre executada fora da thread gráfica."""
    def __init__(self,home):
        super().__init__()
        self.home=home
        self.client=None
        self.pool=QThreadPool.globalInstance()
        self.pending=[]
        self.setStyleSheet("QLabel{color:#DDE7F4}QLineEdit,QComboBox,QListWidget{background:#172231;color:white;border:1px solid #38516d;padding:7px}QPushButton{background:#223957;color:white;padding:10px;border-radius:8px}")
        l=QVBoxLayout(self)
        title=QLabel("Conta HOME — mesmo acesso do Home Hub")
        l.addWidget(title)
        self.status=QLabel("Conecte-se para vincular este computador.");self.status.setWordWrap(True);l.addWidget(self.status)
        self.email=QLineEdit();self.email.setPlaceholderText("E-mail da conta HOME");l.addWidget(self.email)
        self.password=QLineEdit();self.password.setPlaceholderText("Senha");self.password.setEchoMode(QLineEdit.Password);l.addWidget(self.password)
        signin=QPushButton("Entrar com a conta HOME");signin.clicked.connect(self.sign_in);l.addWidget(signin)
        self.model=QComboBox()
        for key,label in [("auto","Automático"),("qwen","Qwen 3"),("glm","GLM"),("nemotron","Nemotron"),("gemma","Gemma"),("llama","Llama"),("granite","Granite")]:self.model.addItem(label,key)
        l.addWidget(self.model)
        self.style=QComboBox()
        for name in ("equilibrado","objetivo","detalhado"):self.style.addItem(name,name)
        l.addWidget(self.style)
        self.sync=QCheckBox("Compartilhar histórico com o HOME HUB (opt-in)");l.addWidget(self.sync)
        save=QPushButton("Salvar preferências da conta");save.clicked.connect(self.save);l.addWidget(save)
        self.list=QListWidget();self.list.itemClicked.connect(self.open_cloud_chat);l.addWidget(self.list)
        self.preview=QLabel("Selecione uma conversa para consultar as mensagens sincronizadas.")
        self.preview.setWordWrap(True);l.addWidget(self.preview)
        upload=QPushButton("Enviar histórico local (somente com sincronização autorizada)")
        upload.clicked.connect(self.upload_local);l.addWidget(upload)
        refresh=QPushButton("Atualizar conversas sincronizadas");refresh.clicked.connect(self.refresh);l.addWidget(refresh)
        signout=QPushButton("Sair da conta neste Windows");signout.clicked.connect(self.sign_out);l.addWidget(signout)
        l.addWidget(QLabel("As funções offline, controles locais e microfone não são enviados para o Hub."))
        self.run_task(lambda:self._resume(),self.connected)
    def run_task(self,work,done):
        task=Task(work)
        task.signals.done.connect(done)
        task.signals.failed.connect(lambda e:self.status.setText(e))
        self.pending.append(task)
        self.pool.start(task)
    def _resume(self):
        self.client=AccountClient()
        return self.client.resume()
    def sign_in(self):
        email=self.email.text().strip();password=self.password.text()
        if not email or not password:return
        self.status.setText("Autenticando...")
        def login():
            if self.client is None:self.client=AccountClient()
            return self.client.login(email,password)
        self.run_task(login,self.connected)
    def connected(self,email):
        if not email:return
        self.password.clear()
        self.status.setText("Conectado como "+email+" · Windows vinculado")
        self.run_task(self.client.get_preferences,self.pref_loaded)
        self.refresh()
    def pref_loaded(self,p):
        self.model.setCurrentIndex(max(0,self.model.findData(p.get("preferred_model","auto"))))
        self.style.setCurrentIndex(max(0,self.style.findData(p.get("response_style","equilibrado"))))
        self.sync.setChecked(p.get("sync_chats",False))
    def save(self):
        if not self.client or not self.client.uid:return
        self.run_task(lambda:self.client.save_preferences(self.model.currentData(),self.style.currentData(),self.sync.isChecked()),
                      lambda _:self.status.setText("Preferências sincronizadas."))
    def refresh(self):
        if not self.client or not self.client.uid:return
        self.run_task(self.client.chats,self.chats_loaded)
    def chats_loaded(self,chats):
        self.list.clear()
        for chat in chats:
            from PySide6.QtWidgets import QListWidgetItem
            item=QListWidgetItem(chat.get("title","Conversa"))
            item.setData(Qt.UserRole,chat.get("id"))
            self.list.addItem(item)
        self.status.setText("Conectado · "+str(len(chats))+" conversas no HOME HUB")
    def open_cloud_chat(self,item):
        if not self.client or not self.client.uid:return
        self.run_task(lambda:self.client.messages(item.data(Qt.UserRole)),self.show_cloud_messages)
    def show_cloud_messages(self,entries):
        preview="\\n\\n".join(("Você" if m.get("role")=="user" else "HOME")+": "+m.get("content","")[:250] for m in entries[-12:])
        self.preview.setText(preview[:1700] or "Conversa vazia.")
    def upload_local(self):
        if not self.client or not self.client.uid:return
        self.status.setText("Enviando conversas autorizadas...")
        self.run_task(lambda:self.client.upload_local(self.home.chat_store),lambda n:(self.status.setText(str(n)+" mensagens sincronizadas."),self.refresh()))
    def sign_out(self):
        if not self.client or not self.client.uid:return
        self.run_task(self.client.logout,lambda _:(self.list.clear(),self.status.setText("Sessão encerrada neste computador.")))
