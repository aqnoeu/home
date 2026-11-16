"""Tests ensure Groq requests are bounded, private and use supported model."""
import json
import unittest
from unittest.mock import patch

from home_groq import MODEL, API, ask_groq, save_key

class _Reply:
    def __init__(self,payload):
        self.payload=payload
    def __enter__(self):
        return self
    def __exit__(self,*exc):
        return False
    def read(self,n):
        return self.payload

class GroqTests(unittest.TestCase):
    def test_model_and_api(self):
        self.assertEqual(MODEL,"openai/gpt-oss-20b")
        self.assertEqual(API,"https://api.groq.com/openai/v1/chat/completions")

    def test_requires_private_key(self):
        with self.assertRaises(RuntimeError):
            ask_groq("Olá",api_key="")

    def test_rejects_oversized_prompt(self):
        with self.assertRaises(ValueError):
            ask_groq("x"*751,api_key="gsk_test")

    def test_does_not_store_key_in_payload(self):
        seen={}
        def mock_open(request,timeout):
            seen["headers"]=dict(request.header_items())
            seen["body"]=json.loads(request.data)
            return _Reply(json.dumps({"choices":[{"message":{"content":"Tudo certo."}}]}).encode())
        with patch("home_groq.urllib.request.urlopen",side_effect=mock_open):
            answer=ask_groq("Oi",history=[{"role":"user","content":"Como está?"}],api_key="gsk_test")
        self.assertEqual(answer,"Tudo certo.")
        self.assertEqual(seen["body"]["model"],MODEL)
        self.assertNotIn("gsk_test",json.dumps(seen["body"]))
        self.assertEqual(seen["body"]["messages"][-1]["content"],"Oi")

    def test_key_validation(self):
        with self.assertRaises(ValueError):
            save_key("invalida")

if __name__=="__main__":
    unittest.main()
