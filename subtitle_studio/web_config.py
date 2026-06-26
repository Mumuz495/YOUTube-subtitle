"""Environment-driven web configuration."""

from __future__ import annotations

import os


TRUTHY_VALUES = {"1", "true", "yes", "on"}
DEFAULT_MAX_REQUEST_BYTES = 8 * 1024 * 1024
DEFAULT_RATE_LIMIT_MAX_REQUESTS = 60
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 10 * 60


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in TRUTHY_VALUES


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def max_request_bytes() -> int:
    return env_int("MAX_REQUEST_BYTES", DEFAULT_MAX_REQUEST_BYTES)


def is_public_deployment() -> bool:
    host = os.environ.get("HOST", "127.0.0.1").strip()
    return (
        env_bool("PUBLIC_DEPLOYMENT")
        or bool(os.environ.get("APP_PASSWORD", "").strip())
        or host in {"0.0.0.0", "::"}
    )


def allow_custom_output_dir() -> bool:
    return env_bool("ALLOW_CUSTOM_OUTPUT_DIR", default=not is_public_deployment())


def resolve_web_output_root(value: str, default_output_dir: str) -> str:
    output = str(value or default_output_dir).strip() or default_output_dir
    if allow_custom_output_dir():
        return output
    return default_output_dir


def rate_limit_enabled() -> bool:
    return env_bool("RATE_LIMIT_ENABLED", default=is_public_deployment())


def rate_limit_max_requests() -> int:
    return env_int("RATE_LIMIT_MAX_REQUESTS", DEFAULT_RATE_LIMIT_MAX_REQUESTS)


def rate_limit_window_seconds() -> int:
    return env_int("RATE_LIMIT_WINDOW_SECONDS", DEFAULT_RATE_LIMIT_WINDOW_SECONDS)
