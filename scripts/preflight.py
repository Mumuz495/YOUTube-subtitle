#!/usr/bin/env python3
"""Pre-deployment checks for Subtitle Studio."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{24,}"),
    re.compile(r"DEEPSEEK_API_KEY\s*=\s*sk-[A-Za-z0-9]{12,}"),
]
REQUIRED_FILES = [
    "app.py",
    "transcript_tool.py",
    "subtitle_studio/__init__.py",
    "subtitle_studio/web_config.py",
    "subtitle_studio/web_limits.py",
    "subtitle_studio/web_paths.py",
    "static/index.html",
    "static/app.js",
    "static/styles.css",
    "requirements.txt",
    "Dockerfile",
    "render.yaml",
    ".dockerignore",
    "DEPLOY_WEBSITE.md",
    "WEBSITE_ARCHITECTURE.md",
    "scripts/smoke_deployment.py",
]
SCAN_EXTENSIONS = {".py", ".js", ".css", ".html", ".md", ".txt", ".yaml", ".yml", ".example"}
SKIP_DIRS = {".git", ".venv", "venv", "env", "output", "__pycache__", "MediaCrawler"}


def run(command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def iter_source_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix in SCAN_EXTENSIONS or path.name in {".env.example", ".gitignore", ".dockerignore", "Dockerfile"}:
            yield path


def check_required_files() -> list[str]:
    issues = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).exists():
            issues.append(f"缺少必需文件：{relative}")
    return issues


def check_no_secrets() -> list[str]:
    issues = []
    for path in iter_source_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                issues.append(f"疑似密钥泄露：{path.relative_to(ROOT)}")
    return issues


def check_gitignore() -> list[str]:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="ignore")
    issues = []
    for expected in (".env", "output/", "__pycache__/", "MediaCrawler/"):
        if expected not in gitignore:
            issues.append(f".gitignore 缺少：{expected}")
    return issues


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    required_issues = check_required_files()
    checks.append(("required files", not required_issues, "\n".join(required_issues)))

    secret_issues = check_no_secrets()
    checks.append(("secret scan", not secret_issues, "\n".join(secret_issues)))

    gitignore_issues = check_gitignore()
    checks.append(("gitignore", not gitignore_issues, "\n".join(gitignore_issues)))

    compile_ok, compile_output = run([
        sys.executable,
        "-m",
        "py_compile",
        "app.py",
        "transcript_tool.py",
        "fetch_transcript.py",
        "daily_run.py",
        "subtitle_studio/__init__.py",
        "subtitle_studio/web_config.py",
        "subtitle_studio/web_limits.py",
        "subtitle_studio/web_paths.py",
        "scripts/smoke_deployment.py",
        "scripts/preflight.py",
    ])
    checks.append(("python compile", compile_ok, compile_output))

    tests_ok, tests_output = run([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
    checks.append(("unit tests", tests_ok, tests_output))

    all_ok = True
    for name, ok, detail in checks:
        mark = "OK" if ok else "FAIL"
        print(f"[{mark}] {name}")
        if detail and (not ok or os.environ.get("PREFLIGHT_VERBOSE")):
            print(detail)
        all_ok = all_ok and ok

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
