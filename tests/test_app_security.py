import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app import DEFAULT_OUTPUT_DIR, ROOT, _resolve_download_path, _resolve_web_output_root


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


if __name__ == "__main__":
    unittest.main()
