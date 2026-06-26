import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app import (
    DEFAULT_OUTPUT_DIR,
    ROOT,
    STATIC_DIR,
    _max_request_bytes,
    _resolve_download_path,
    _resolve_static_path,
    _resolve_web_output_root,
)


class WebAppSecurityTests(unittest.TestCase):
    def test_public_deployment_ignores_custom_output_directory(self):
        with patch.dict(os.environ, {"PUBLIC_DEPLOYMENT": "1", "ALLOW_CUSTOM_OUTPUT_DIR": ""}, clear=True):
            self.assertEqual(_resolve_web_output_root("../outside"), DEFAULT_OUTPUT_DIR)

    def test_local_mode_allows_custom_output_directory(self):
        with patch.dict(os.environ, {"HOST": "127.0.0.1"}, clear=True):
            self.assertEqual(_resolve_web_output_root("my-output"), "my-output")

    def test_download_path_must_stay_inside_output_directory(self):
        out_file = ROOT / DEFAULT_OUTPUT_DIR / "download-security-test.txt"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text("ok", encoding="utf-8")
        try:
            self.assertEqual(_resolve_download_path(str(Path(DEFAULT_OUTPUT_DIR) / out_file.name)), out_file.resolve())
        finally:
            out_file.unlink(missing_ok=True)

    def test_download_path_rejects_env_file(self):
        with self.assertRaises(FileNotFoundError):
            _resolve_download_path(".env")

    def test_static_path_must_stay_inside_static_directory(self):
        with self.assertRaises(FileNotFoundError):
            _resolve_static_path(STATIC_DIR / ".." / "app.py")

    def test_max_request_bytes_uses_safe_default_for_invalid_env(self):
        with patch.dict(os.environ, {"MAX_REQUEST_BYTES": "not-a-number"}, clear=True):
            self.assertEqual(_max_request_bytes(), 8 * 1024 * 1024)

    def test_max_request_bytes_can_be_configured(self):
        with patch.dict(os.environ, {"MAX_REQUEST_BYTES": "1024"}, clear=True):
            self.assertEqual(_max_request_bytes(), 1024)


if __name__ == "__main__":
    unittest.main()
