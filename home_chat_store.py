"""Local persistent chat history, no credentials or audio. Atomic file writes."""
import json
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path

ROOT=Path(os.environ.get("LOCALAPPDATA") or Path.home()/".local"/"share")/"Home"
MAX_CHATS=100
MAX_MESSAGES=250

class ChatStore:
    def __init__(self,path=None):
        self.path=Path(path) if path else ROOT/"conversations.json"
        self.lock=threading.RLock()
        self.data={"active":"","chats":[]}
        try:
            loaded=json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded,dict) and isinstance(loaded.get("chats"),list):
                self.data=loaded
        except (OSError,ValueError,TypeError):
            pass

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix=".home-chat-",dir=self.path.parent)
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as f:
                json.dump(self.data,f,ensure_ascii=False,indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name,self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def all(self):
        with self.lock:
            return sorted([{"id":c["id"],"title":c.get("title","Conversa"),
                            "updated":c.get("updated",0)} for c in self.data["chats"]],
                          key=lambda c:c["updated"],reverse=True)

    def _find(self,id):
        return next((c for c in self.data["chats"] if c["id"]==id),None)

    def new(self):
        with self.lock:
            id=str(uuid.uuid4())
            now=time.time()
            self.data["chats"].append({"id":id,"title":"Nova conversa",
                                       "created":now,"updated":now,"messages":[]})
            self.data["chats"]=self.data["chats"][-MAX_CHATS:]
            self.data["active"]=id
            self._save()
            return id

    def select(self,id):
        with self.lock:
            if self._find(id) is None:
                raise ValueError("Conversa não encontrada.")
            self.data["active"]=id
            self._save()

    def active(self):
        with self.lock:
            id=self.data.get("active","")
            return id if self._find(id) is not None else self.new()

    def delete(self,id):
        with self.lock:
            self.data["chats"]=[c for c in self.data["chats"] if c["id"]!=id]
            if self.data.get("active")==id:
                self.data["active"]=""
            self._save()

    def messages(self,id=None):
        with self.lock:
            chat=self._find(id or self.active())
            return list(chat.get("messages",[])) if chat else []

    def add(self,role,text,id=None):
        if role not in ("user","home") or not isinstance(text,str) or not text.strip():
            return
        with self.lock:
            chat=self._find(id or self.active())
            if chat is None:
                return
            content=text.strip()[:1200]
            chat["messages"].append({"role":role,"text":content,"time":time.time()})
            chat["messages"]=chat["messages"][-MAX_MESSAGES:]
            if role=="user" and chat["title"]=="Nova conversa":
                chat["title"]=content[:55]
            chat["updated"]=time.time()
            self._save()

    def context(self,id=None):
        return [{"role":"assistant" if m["role"]=="home" else "user",
                 "content":m["text"]} for m in self.messages(id)[-8:]]
