"""API security primitives: API-key authentication and rate limiting."""

import time
from collections import defaultdict
from typing import Callable, Optional


def check_api_key(header_value: Optional[str], expected: Optional[str]) -> bool:
    """Return True when the provided key matches the expected key (expected None -> deny)."""
    if expected is None:
        return False
    return header_value == expected


class FixedWindowRateLimiter:
    """In-memory fixed-window rate limiter with an injectable clock (test seam)."""

    def __init__(
        self,
        enabled: bool = False,
        limit: int = 60,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.enabled = enabled
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        """Return True if the request is allowed under the current window."""
        if not self.enabled:
            return True
        now = self._clock()
        window_start = now - self.window_seconds
        recent = [t for t in self._hits[key] if t > window_start]
        if len(recent) >= self.limit:
            self._hits[key] = recent
            return False
        recent.append(now)
        self._hits[key] = recent
        return True
