"""Cleanup helpers for generated public deployment files."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .web_config import output_retention_hours
from .web_paths import output_dir


@dataclass(frozen=True)
class CleanupResult:
    scanned: int = 0
    removed_files: int = 0
    removed_dirs: int = 0


def cleanup_generated_output(default_output_dir: str, now: float | None = None) -> CleanupResult:
    retention_hours = output_retention_hours()
    if retention_hours <= 0:
        return CleanupResult()

    root = output_dir(default_output_dir)
    if not root.exists():
        return CleanupResult()

    current = time.time() if now is None else now
    cutoff = current - retention_hours * 3600
    scanned = 0
    removed_files = 0
    removed_dirs = 0

    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        scanned += 1
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed_files += 1
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
                removed_dirs += 1
        except OSError:
            continue

    return CleanupResult(scanned=scanned, removed_files=removed_files, removed_dirs=removed_dirs)
