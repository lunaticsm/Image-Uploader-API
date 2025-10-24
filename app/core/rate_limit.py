from __future__ import annotations

import threading
from time import monotonic
from typing import Dict, Tuple


class RateLimiter:
    """Fixed window rate limiter stored in-memory per client."""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = max(limit, 1)
        self.window_seconds = window_seconds
        self._clients: Dict[str, Tuple[int, float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> Tuple[bool, int]:
        """
        Register a hit for the given key.
        Returns (allowed, retry_after_seconds).
        """
        now = monotonic()
        with self._lock:
            count, reset_at = self._clients.get(key, (0, now + self.window_seconds))
            if now > reset_at:
                count = 0
                reset_at = now + self.window_seconds
            if count >= self.limit:
                retry_after = max(0, int(reset_at - now))
                return False, retry_after or 1

            self._clients[key] = (count + 1, reset_at)
            retry_after = max(0, int(reset_at - now))
            return True, retry_after
