import os
import unittest
from pathlib import Path
from unittest.mock import patch

from transcript_tool import DEFAULT_OUTPUT_DIR
from subtitle_studio.web_config import (
    max_request_bytes,
    rate_limit_enabled,
    resolve_web_output_root,
)
from subtitle_studio.web_limits import InMemoryRateLimiter, client_key
from subtitle_studio.web_paths import ROOT, STATIC_DIR, resolve_download_path, resolve_static_path


class WebAppSecurityTests(unittest.TestCase):
    def test_public_deployment_ignores_custom_output_directory(self):
        with patch.dict(os.environ, {"PUBLIC_DEPLOYMENT": "1", "ALLOW_CUSTOM_OUTPUT_DIR": ""}, clear=True):
            self.assertEqual(resolve_web_output_root("../outside", DEFAULT_OUTPUT_DIR), DEFAULT_OUTPUT_DIR)

    def test_local_mode_allows_custom_output_directory(self):
        with patch.dict(os.environ, {"HOST": "127.0.0.1"}, clear=True):
            self.assertEqual(resolve_web_output_root("my-output", DEFAULT_OUTPUT_DIR), "my-output")

    def test_download_path_must_stay_inside_output_directory(self):
        out_file = ROOT / DEFAULT_OUTPUT_DIR / "download-security-test.txt"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text("ok", encoding="utf-8")
        try:
            self.assertEqual(
                resolve_download_path(str(Path(DEFAULT_OUTPUT_DIR) / out_file.name), DEFAULT_OUTPUT_DIR),
                out_file.resolve(),
            )
        finally:
            out_file.unlink(missing_ok=True)

    def test_download_path_rejects_env_file(self):
        with self.assertRaises(FileNotFoundError):
            resolve_download_path(".env", DEFAULT_OUTPUT_DIR)

    def test_static_path_must_stay_inside_static_directory(self):
        with self.assertRaises(FileNotFoundError):
            resolve_static_path(STATIC_DIR / ".." / "app.py")

    def test_max_request_bytes_uses_safe_default_for_invalid_env(self):
        with patch.dict(os.environ, {"MAX_REQUEST_BYTES": "not-a-number"}, clear=True):
            self.assertEqual(max_request_bytes(), 8 * 1024 * 1024)

    def test_max_request_bytes_can_be_configured(self):
        with patch.dict(os.environ, {"MAX_REQUEST_BYTES": "1024"}, clear=True):
            self.assertEqual(max_request_bytes(), 1024)

    def test_rate_limit_defaults_to_off_for_local_mode(self):
        with patch.dict(os.environ, {"HOST": "127.0.0.1"}, clear=True):
            self.assertFalse(rate_limit_enabled())

    def test_rate_limit_defaults_to_on_for_public_mode(self):
        with patch.dict(os.environ, {"PUBLIC_DEPLOYMENT": "1"}, clear=True):
            self.assertTrue(rate_limit_enabled())

    def test_rate_limiter_blocks_after_configured_limit(self):
        limiter = InMemoryRateLimiter()
        env = {
            "RATE_LIMIT_ENABLED": "1",
            "RATE_LIMIT_MAX_REQUESTS": "2",
            "RATE_LIMIT_WINDOW_SECONDS": "60",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(limiter.check("client", now=100.0).allowed)
            self.assertTrue(limiter.check("client", now=101.0).allowed)
            blocked = limiter.check("client", now=102.0)

        self.assertFalse(blocked.allowed)
        self.assertGreaterEqual(blocked.retry_after, 1)

    def test_rate_limiter_expires_old_requests(self):
        limiter = InMemoryRateLimiter()
        env = {
            "RATE_LIMIT_ENABLED": "1",
            "RATE_LIMIT_MAX_REQUESTS": "1",
            "RATE_LIMIT_WINDOW_SECONDS": "10",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(limiter.check("client", now=100.0).allowed)
            self.assertTrue(limiter.check("client", now=111.0).allowed)

    def test_client_key_prefers_forwarded_for(self):
        headers = {"X-Forwarded-For": "203.0.113.10, 10.0.0.1"}
        self.assertEqual(client_key(headers, ("127.0.0.1", 1234)), "203.0.113.10")


if __name__ == "__main__":
    unittest.main()
