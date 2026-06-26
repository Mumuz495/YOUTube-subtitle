"""Small in-memory rate limiter for shared public deployments."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from http import HTTPStatus

from .web_config import rate_limit_enabled, rate_limit_max_requests, rate_limit_window_seconds


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: int = 0


class InMemoryRateLimiter:
    def __init__(self):
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> RateLimitResult:
        if not rate_limit_enabled():
            return RateLimitResult(allowed=True)

        current = time.monotonic() if now is None else now
        window = rate_limit_window_seconds()
        max_requests = rate_limit_max_requests()
        cutoff = current - window

        with self._lock:
            requests = self._requests[key]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= max_requests:
                retry_after = max(1, int(round(window - (current - requests[0]))))
                return RateLimitResult(allowed=False, retry_after=retry_after)
            requests.append(current)
            return RateLimitResult(allowed=True)


def client_key(headers, client_address) -> str:
    forwarded_for = headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
    if forwarded_for:
        return forwarded_for
    if client_address:
        return str(client_address[0])
    return "unknown"


RATE_LIMITER = InMemoryRateLimiter()
RATE_LIMIT_STATUS = HTTPStatus.TOO_MANY_REQUESTS
