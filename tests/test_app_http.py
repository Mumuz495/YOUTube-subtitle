import json
import os
import base64
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import app
from app import TranscriptAppHandler
from subtitle_studio.web_limits import InMemoryRateLimiter


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

    def test_post_requests_are_rate_limited_when_enabled(self):
        env = {
            "RATE_LIMIT_ENABLED": "1",
            "RATE_LIMIT_MAX_REQUESTS": "1",
            "RATE_LIMIT_WINDOW_SECONDS": "60",
        }
        with patch.dict(os.environ, env, clear=True), patch.object(app, "RATE_LIMITER", InMemoryRateLimiter()):
            base_url = self._with_server()
            payload = b"{}"
            first = urllib.request.Request(
                f"{base_url}/api/fetch",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as first_error:
                urllib.request.urlopen(first, timeout=5)
            self.assertEqual(first_error.exception.code, 400)

            second = urllib.request.Request(
                f"{base_url}/api/fetch",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as second_error:
                urllib.request.urlopen(second, timeout=5)

        self.assertEqual(second_error.exception.code, 429)
        self.assertEqual(second_error.exception.headers["Retry-After"], "60")

    def test_pdf_upload_endpoint_returns_processed_result(self):
        with patch.dict(os.environ, {}, clear=True):
            base_url = self._with_server()
            with patch("app.process_pdf_upload") as process_pdf_upload:
                process_pdf_upload.return_value = {
                    "ok": True,
                    "source_type": "pdf",
                    "title": "sample.pdf",
                    "files": {"txt": "output/pdf_sample/transcript.txt"},
                    "preview": [{"text": "Readable PDF text.", "start": 0, "duration": 0}],
                    "full": [{"text": "Readable PDF text.", "start": 0, "duration": 0}],
                }
                request = urllib.request.Request(
                    f"{base_url}/api/pdf",
                    data=json.dumps(
                        {
                            "filename": "sample.pdf",
                            "pdf_file": base64.b64encode(b"%PDF test").decode("ascii"),
                            "output": "output",
                        }
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["results"][0]["source_type"], "pdf")
        process_pdf_upload.assert_called_once()
        self.assertEqual(process_pdf_upload.call_args.args[0], b"%PDF test")
        self.assertEqual(process_pdf_upload.call_args.args[1], "sample.pdf")

    def test_pdf_multipart_upload_endpoint_returns_processed_result(self):
        with patch.dict(os.environ, {}, clear=True):
            base_url = self._with_server()
            with patch("app.process_pdf_upload") as process_pdf_upload:
                process_pdf_upload.return_value = {
                    "ok": True,
                    "source_type": "pdf",
                    "title": "sample.pdf",
                    "files": {"txt": "output/pdf_sample/transcript.txt"},
                    "preview": [{"text": "Readable PDF text.", "start": 0, "duration": 0}],
                    "full": [{"text": "Readable PDF text.", "start": 0, "duration": 0}],
                }
                from tests.test_web_multipart import build_multipart_body

                body, content_type = build_multipart_body(
                    fields={"output": "output", "translate": "false"},
                    files={"pdf": ("sample.pdf", b"%PDF multipart", "application/pdf")},
                )
                request = urllib.request.Request(
                    f"{base_url}/api/pdf-upload",
                    data=body,
                    headers={"Content-Type": content_type},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["results"][0]["source_type"], "pdf")
        process_pdf_upload.assert_called_once()
        self.assertEqual(process_pdf_upload.call_args.args[0], b"%PDF multipart")
        self.assertEqual(process_pdf_upload.call_args.args[1], "sample.pdf")

    def test_pdf_multipart_upload_rejects_oversized_file(self):
        env = {"PDF_MAX_UPLOAD_BYTES": "32"}
        with patch.dict(os.environ, env, clear=True):
            base_url = self._with_server()
            from tests.test_web_multipart import build_multipart_body

            body, content_type = build_multipart_body(
                files={"pdf": ("big.pdf", b"x" * 64, "application/pdf")},
            )
            request = urllib.request.Request(
                f"{base_url}/api/pdf-upload",
                data=body,
                headers={"Content-Type": content_type},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=5)

        self.assertEqual(raised.exception.code, 400)
        payload = json.loads(raised.exception.read().decode("utf-8"))
        self.assertFalse(payload["ok"])
        self.assertIn("超过上传上限", payload["error"])

    def test_pdf_multipart_upload_saves_original_pdf_copy(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            base_url = self._with_server()
            with patch("app.process_pdf_upload") as process_pdf_upload:
                process_pdf_upload.return_value = {
                    "ok": True,
                    "source_type": "pdf",
                    "title": "sample.pdf",
                    "files": {"txt": str(Path(tmp) / "pdf_sample" / "transcript.txt")},
                    "preview": [{"text": "Readable PDF text.", "start": 0, "duration": 0}],
                    "full": [{"text": "Readable PDF text.", "start": 0, "duration": 0}],
                }
                from tests.test_web_multipart import build_multipart_body

                body, content_type = build_multipart_body(
                    fields={"output": tmp, "translate": "false"},
                    files={"pdf": ("sample.pdf", b"%PDF original", "application/pdf")},
                )
                request = urllib.request.Request(
                    f"{base_url}/api/pdf-upload",
                    data=body,
                    headers={"Content-Type": content_type},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    json.loads(response.read().decode("utf-8"))

            saved = list((Path(tmp) / "uploads").glob("*.pdf"))
            saved_count = len(saved)
            saved_content = saved[0].read_bytes() if saved else b""

        self.assertEqual(response.status, 200)
        self.assertEqual(saved_count, 1)
        self.assertEqual(saved_content, b"%PDF original")

    def test_config_endpoint_exposes_pdf_upload_limit(self):
        env = {"PDF_MAX_UPLOAD_BYTES": str(200 * 1024 * 1024)}
        with patch.dict(os.environ, env, clear=True):
            base_url = self._with_server()
            with urllib.request.urlopen(f"{base_url}/api/config", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["pdf_max_upload_bytes"], 200 * 1024 * 1024)
        self.assertEqual(payload["pdf_max_upload_label"], "200 MB")


if __name__ == "__main__":
    unittest.main()
