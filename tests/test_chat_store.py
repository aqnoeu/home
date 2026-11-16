import tempfile
import unittest
from pathlib import Path

from home_chat_store import ChatStore

class ChatTests(unittest.TestCase):
    def test_persists_conversation_after_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/"chats.json"
            store=ChatStore(file)
            a=store.new()
            store.add("user","Primeira pergunta")
            store.add("home","Primeira resposta")
            b=store.new()
            store.add("user","Outra conversa")
            restored=ChatStore(file)
            self.assertEqual(restored.active(),b)
            self.assertEqual(len(restored.all()),2)
            restored.select(a)
            self.assertEqual(len(restored.messages()),2)
            self.assertEqual(restored.context()[-1]["content"],"Primeira resposta")

    def test_delete_keeps_other_chats(self):
        with tempfile.TemporaryDirectory() as temp:
            store=ChatStore(Path(temp)/"chats.json")
            a=store.new()
            b=store.new()
            store.delete(a)
            self.assertEqual(len(store.all()),1)
            self.assertEqual(store.active(),b)

    def test_only_text_and_roles(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/"chats.json"
            store=ChatStore(file)
            store.add("secret","gsk_example")
            store.add("user","Olá")
            self.assertEqual(len(store.messages()),1)
            self.assertNotIn("gsk_example",file.read_text(encoding="utf-8"))

if __name__=="__main__":
    unittest.main()
