#!/usr/bin/env python3
"""Smoke-test a running Subtitle Studio deployment."""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def request(url: str, username: str | None = None, password: str | None = None) -> tuple[int, bytes]:
    headers = {}
    if username and password:
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a Subtitle Studio website.")
    parser.add_argument("base_url", help="Deployment URL, for example https://subtitle-studio.onrender.com")
    parser.add_argument("--username", default="friend", help="Basic-auth username")
    parser.add_argument("--password", default="", help="Basic-auth password")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    checks: list[tuple[str, bool, str]] = []

    health_status, health_body = request(f"{base_url}/healthz")
    health_ok = False
    try:
        health_payload = json.loads(health_body.decode("utf-8"))
        health_ok = health_status == 200 and health_payload.get("ok") is True
    except json.JSONDecodeError:
        health_ok = False
    checks.append(("healthz", health_ok, f"status={health_status}"))

    public_status, _ = request(f"{base_url}/")
    if args.password:
        checks.append(("password gate", public_status == 401, f"status={public_status}"))
        home_status, home_body = request(f"{base_url}/", args.username, args.password)
    else:
        checks.append(("public home", public_status == 200, f"status={public_status}"))
        home_status, home_body = public_status, b""

    home_ok = home_status == 200 and (not home_body or b"Subtitle Studio" in home_body)
    checks.append(("authorized home", home_ok, f"status={home_status}"))

    env_path = urllib.parse.quote(".env")
    blocked_status, _ = request(f"{base_url}/download?path={env_path}", args.username, args.password)
    checks.append(("blocked .env download", blocked_status in {401, 404}, f"status={blocked_status}"))

    for name, ok, detail in checks:
        mark = "OK" if ok else "FAIL"
        print(f"[{mark}] {name}: {detail}")

    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
