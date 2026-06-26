import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from app import TranscriptAppHandler


class AppHttpTests(unittest.TestCase):
    def _with_server(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), TranscriptAppHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.addCleanup(cleanup)
        return f"http://127.0.0.1:{server.server_port}"

    def test_healthz_does_not_require_password(self):
        with patch.dict(os.environ, {"APP_PASSWORD": "secret", "APP_USERNAME": "friend"}, clear=True):
            base_url = self._with_server()
            with urllib.request.urlopen(f"{base_url}/healthz", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "subtitle-studio")

    def test_home_requires_password_when_configured(self):
        with patch.dict(os.environ, {"APP_PASSWORD": "secret", "APP_USERNAME": "friend"}, clear=True):
            base_url = self._with_server()
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(f"{base_url}/", timeout=5)

        self.assertEqual(raised.exception.code, 401)


if __name__ == "__main__":
    unittest.main()
