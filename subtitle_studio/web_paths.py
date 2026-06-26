"""Path resolution helpers for the web app."""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"


def output_dir(default_output_dir: str) -> Path:
    return (ROOT / default_output_dir).resolve()


def resolve_download_path(raw_path: str, default_output_dir: str) -> Path:
    resolved = (ROOT / raw_path).resolve() if not os.path.isabs(raw_path) else Path(raw_path).resolve()
    try:
        resolved.relative_to(output_dir(default_output_dir))
    except ValueError as exc:
        raise FileNotFoundError from exc
    if not resolved.is_file():
        raise FileNotFoundError
    return resolved


def resolve_static_path(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(STATIC_DIR.resolve())
    except ValueError as exc:
        raise FileNotFoundError from exc
    if not resolved.is_file():
        raise FileNotFoundError
    return resolved
