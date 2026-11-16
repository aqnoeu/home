"""Offline tests for credential and Groq API error handling."""
import io
import json
import unittest
import urllib.error
from unittest.mock import patch

import home_groq


class FakeResponse:
    def __init__(self, payload):
        self.data = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.data[:size]


def http_error(code, message="blocked", error_code="model_permission_blocked_project"):
    data = json.dumps({"error": {"code": error_code, "message": message}}).encode()
    return urllib.error.HTTPError(
        home_groq.API, code, "error", {}, io.BytesIO(data)
    )


class TestGroqClient(unittest.TestCase):
    def test_credentials_are_read_back(self):
        vault = {}
        with patch.dict("sys.modules", {"keyring": __import__("types").SimpleNamespace(
            set_password=lambda service, account, value: vault.__setitem__((service, account), value),
            get_password=lambda service, account: vault.get((service, account))
        )}):
            self.assertTrue(home_groq.save_key("gsk_" + "A" * 32))
            self.assertEqual(home_groq.get_key(), "gsk_" + "A" * 32)

    def test_403_primary_falls_back_to_authorized_model(self):
        calls = []
        def urlopen(request, timeout=0):
            body = json.loads(request.data)
            calls.append(body["model"])
            if len(calls) == 1:
                raise http_error(403)
            self.assertNotIn("reasoning_effort", body)
            return FakeResponse({"choices": [{"message": {
                "content": json.dumps({"resposta": "Olá", "emocao": "neutro"})
            }}]})
        with patch("home_groq.urllib.request.urlopen", side_effect=urlopen):
            response, emotion = home_groq.ask_groq(
                "Oi", api_key="gsk_" + "B" * 32, structured=True
            )
        self.assertEqual(response, "Olá")
        self.assertEqual(emotion, "neutro")
        self.assertEqual(calls, [home_groq.MODEL, home_groq.FALLBACK_MODELS[0]])

    def test_no_fallback_for_401(self):
        calls = []
        def urlopen(request, timeout=0):
            calls.append(request)
            raise http_error(401, error_code="")
        with patch("home_groq.urllib.request.urlopen", side_effect=urlopen):
            with self.assertRaisesRegex(RuntimeError, "401"):
                home_groq.ask_groq("Oi", api_key="gsk_" + "C" * 32)
        self.assertEqual(len(calls), 1)

    def test_all_models_blocked_reports_failure(self):
        with patch("home_groq.urllib.request.urlopen", side_effect=http_error(403)):
            with self.assertRaisesRegex(RuntimeError, "todos os modelos"):
                home_groq.ask_groq("Oi", api_key="gsk_" + "D" * 32)

    def test_model_listing_is_not_confused_with_chat(self):
        response = FakeResponse({"data": [{"id": "model-x"}]})
        with patch("home_groq.urllib.request.urlopen", return_value=response):
            self.assertTrue(home_groq.verify_groq_credentials("gsk_" + "E" * 32))


if __name__ == "__main__":
    unittest.main()
