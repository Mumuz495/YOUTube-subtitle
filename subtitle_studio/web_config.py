"""Environment-driven web configuration."""

from __future__ import annotations

import os


TRUTHY_VALUES = {"1", "true", "yes", "on"}
DEFAULT_MAX_REQUEST_BYTES = 8 * 1024 * 1024
DEFAULT_PDF_MAX_UPLOAD_BYTES = 200 * 1024 * 1024
DEFAULT_RATE_LIMIT_MAX_REQUESTS = 60
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 10 * 60
DEFAULT_PUBLIC_OUTPUT_RETENTION_HOURS = 24


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


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


def max_request_bytes() -> int:
    return env_int("MAX_REQUEST_BYTES", DEFAULT_MAX_REQUEST_BYTES)


def pdf_max_upload_bytes() -> int:
    return env_int("PDF_MAX_UPLOAD_BYTES", DEFAULT_PDF_MAX_UPLOAD_BYTES)


def pdf_max_upload_label() -> str:
    size = pdf_max_upload_bytes()
    mb = size / 1024 / 1024
    if mb >= 10 and abs(mb - round(mb)) < 0.05:
        return f"{int(round(mb))} MB"
    return f"{mb:.1f} MB"


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


def output_retention_hours() -> float:
    default = DEFAULT_PUBLIC_OUTPUT_RETENTION_HOURS if is_public_deployment() else 0.0
    return env_float("OUTPUT_RETENTION_HOURS", default)
