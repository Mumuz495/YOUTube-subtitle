#!/usr/bin/env python3
"""Local web app for grabbing YouTube transcripts for language study."""

from __future__ import annotations

import json
import mimetypes
import os
import base64
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from subtitle_studio.web_limits import RATE_LIMITER, RATE_LIMIT_STATUS, client_key
from subtitle_studio.web_config import max_request_bytes, resolve_web_output_root
from subtitle_studio.web_paths import ROOT, STATIC_DIR, resolve_download_path, resolve_static_path
from transcript_tool import (
    DEFAULT_OUTPUT_DIR,
    analyze_vocab_term,
    generate_tts_audio,
    get_deepseek_api_key,
    process_url,
    save_study_sheet_html,
)


class TranscriptAppHandler(BaseHTTPRequestHandler):
    server_version = "SubtitleStudio/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._send_json({"ok": True, "service": "subtitle-studio"})
            return

        if not self._ensure_authorized():
            return

        if parsed.path == "/":
            self._send_file(STATIC_DIR / "index.html")
            return
        if parsed.path.startswith("/static/"):
            self._send_file(STATIC_DIR / parsed.path.removeprefix("/static/"))
            return
        if parsed.path == "/download":
            self._send_download(parsed.query)
            return
        self._send_json({"ok": False, "error": "Not found"}, status=404)

    def do_POST(self):
        if not self._ensure_authorized():
            return
        if not self._ensure_rate_limit():
            return

        parsed_path = urlparse(self.path).path
        if parsed_path == "/api/vocab":
            self._handle_vocab_request()
            return
        if parsed_path == "/api/export-study-sheet":
            self._handle_study_sheet_export()
            return
        if parsed_path == "/api/tts":
            self._handle_tts_request()
            return

        if parsed_path != "/api/fetch":
            self._send_json({"ok": False, "error": "Not found"}, status=404)
            return

        try:
            payload = self._read_json_body()
            url = str(payload.get("url", "")).strip()
            output = resolve_web_output_root(str(payload.get("output", DEFAULT_OUTPUT_DIR)), DEFAULT_OUTPUT_DIR)
            translate = bool(payload.get("translate", False))
            limit = _coerce_limit(payload.get("limit"))

            if not url:
                raise ValueError("请先粘贴视频或文章链接。")

            result = process_url(url, output_root=output, translate=translate, limit=limit)
            self._send_json(result)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)

    def _handle_study_sheet_export(self):
        try:
            payload = self._read_json_body()
            html = str(payload.get("html", ""))
            output = resolve_web_output_root(str(payload.get("output", DEFAULT_OUTPUT_DIR)), DEFAULT_OUTPUT_DIR)
            export_format = str(payload.get("format", "html")).strip() or "html"
            path = save_study_sheet_html(html, output, export_format=export_format)
            self._send_json({"ok": True, "file": path})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)

    def _handle_vocab_request(self):
        try:
            payload = self._read_json_body()
            term = str(payload.get("term", "")).strip()
            context = str(payload.get("context", "")).strip()
            api_key = get_deepseek_api_key()

            if not api_key:
                raise ValueError("未设置 DEEPSEEK_API_KEY，无法处理生词。")

            result = analyze_vocab_term(term, context, api_key)
            self._send_json({"ok": True, "entry": result})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)

    def _handle_tts_request(self):
        try:
            payload = self._read_json_body()
            text = str(payload.get("text", "")).strip()
            output = resolve_web_output_root(str(payload.get("output", DEFAULT_OUTPUT_DIR)), DEFAULT_OUTPUT_DIR)
            voice_profile = str(payload.get("voice_profile", "us-female")).strip() or "us-female"
            rate = str(payload.get("rate", "1")).strip() or "1"
            path = generate_tts_audio(text, output_root=output, voice_profile=voice_profile, rate=rate)
            self._send_json({"ok": True, "file": path, "url": f"/download?path={path}"})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > max_request_bytes():
            raise ValueError("请求内容过大，请缩短文本或分批处理。")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _ensure_authorized(self) -> bool:
        password = os.environ.get("APP_PASSWORD", "").strip()
        if not password:
            return True

        username = os.environ.get("APP_USERNAME", "friend").strip() or "friend"
        header = self.headers.get("Authorization", "")
        prefix = "Basic "
        if header.startswith(prefix):
            try:
                decoded = base64.b64decode(header[len(prefix):]).decode("utf-8")
                supplied_username, supplied_password = decoded.split(":", 1)
                if hmac.compare_digest(supplied_username, username) and hmac.compare_digest(supplied_password, password):
                    return True
            except (ValueError, UnicodeDecodeError):
                pass

        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Subtitle Studio"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("需要访问密码。".encode("utf-8"))
        return False

    def _ensure_rate_limit(self) -> bool:
        result = RATE_LIMITER.check(client_key(self.headers, self.client_address))
        if result.allowed:
            return True

        self.send_response(RATE_LIMIT_STATUS)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Retry-After", str(result.retry_after))
        content = json.dumps(
            {"ok": False, "error": f"请求太频繁，请 {result.retry_after} 秒后再试。"},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
        return False

    def _send_file(self, path: Path):
        try:
            resolved = resolve_static_path(path)
            content = resolved.read_bytes()
        except FileNotFoundError:
            self._send_json({"ok": False, "error": "File not found"}, status=404)
            return

        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type = f"{content_type}; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_download(self, query: str):
        params = parse_qs(query)
        raw_path = unquote(params.get("path", [""])[0])
        if not raw_path:
            self._send_json({"ok": False, "error": "Missing path"}, status=400)
            return

        try:
            resolved = resolve_download_path(raw_path, DEFAULT_OUTPUT_DIR)
            content = resolved.read_bytes()
        except FileNotFoundError:
            self._send_json({"ok": False, "error": "File not found"}, status=404)
            return

        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        if content_type.startswith("text/"):
            content_type = f"{content_type}; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{resolved.name}"')
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, data: dict, status: int = 200):
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def _coerce_limit(value) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    limit = int(value)
    if limit < 1:
        return None
    return min(limit, 50)


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer((host, port), TranscriptAppHandler)
    print(f"Subtitle Studio running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
