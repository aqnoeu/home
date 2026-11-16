"""Contrato de IA compartilhado Home Windows/Android sem rede externa."""
import io
import unittest
from unittest.mock import patch

from home_ai import ask_home_ai, save_ai_settings


class HomeAiTests(unittest.TestCase):
    def test_requires_https(self):
        with self.assertRaises(ValueError):
            ask_home_ai("oi",0,"http://not-secure.invalid/ai","token")

    def test_json_reply(self):
        stream=io.BytesIO(b'{"reply":"Oi!","mood":1}')
        with patch("home_ai.urllib.request.urlopen",return_value=stream) as mocked:
            result=ask_home_ai("oi",0,"https://example.org/ai","home-token")
        self.assertEqual(result,("Oi!",1))
        req=mocked.call_args[0][0]
        self.assertEqual(req.get_header("Authorization"),"Bearer home-token")

    def test_untrusted_url_rejected(self):
        with self.assertRaises(ValueError):
            save_ai_settings("https://user:pass@example.org/ai","x")


if __name__=="__main__":
    unittest.main()
