from __future__ import annotations

import threading
from time import monotonic
from typing import Dict, Tuple, Optional
from app.config import REDIS_URL


class RateLimiter:
    """Fixed window rate limiter with Redis or in-memory storage per client."""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = max(limit, 1)
        self.window_seconds = window_seconds
        # Check if Redis is available
        self.use_redis = self._check_redis_availability()

        if self.use_redis:
            import redis
            self._redis_client = redis.from_url(REDIS_URL)
        else:
            self._clients: Dict[str, Tuple[int, float]] = {}
            self._lock = threading.Lock()

    def _check_redis_availability(self) -> bool:
        """Check if Redis is configured and available."""
        if not REDIS_URL:
            return False

        try:
            import redis
            client = redis.from_url(REDIS_URL)
            client.ping()
            return True
        except (ImportError, Exception):
            return False

    def hit(self, key: str) -> Tuple[bool, int]:
        """
        Register a hit for the given key.
        Returns (allowed, retry_after_seconds).
        """
        if self.use_redis:
            return self._hit_redis(key)
        else:
            return self._hit_memory(key)

    def _hit_redis(self, key: str) -> Tuple[bool, int]:
        """Redis-based rate limiting implementation."""
        import redis
        from time import time

        now = time()
        window_end = now + self.window_seconds

        # Use Redis with a key that includes the time window
        redis_key = f"rate_limit:{key}"

        try:
            # Get current count and reset time
            pipe = self._redis_client.pipeline()
            pipe.get(f"{redis_key}:count")
            pipe.get(f"{redis_key}:reset")
            pipe.expire(f"{redis_key}:count", int(self.window_seconds))
            pipe.expire(f"{redis_key}:reset", int(self.window_seconds))
            results = pipe.execute()

            current_count_str = results[0]
            reset_time_str = results[1]

            if current_count_str is None:
                # First request in this window
                current_count = 1
                reset_time = window_end
            else:
                current_count = int(current_count_str)
                reset_time = float(reset_time_str) if reset_time_str else window_end

                if now > reset_time:
                    # Window has expired, reset
                    current_count = 1
                    reset_time = window_end
                else:
                    # Increment count
                    current_count += 1

            if current_count > self.limit:
                # Rate limit exceeded
                retry_after = max(0, int(reset_time - now))
                return False, retry_after or 1

            # Update Redis with new values
            pipe = self._redis_client.pipeline()
            pipe.setex(f"{redis_key}:count", int(self.window_seconds), str(current_count))
            pipe.setex(f"{redis_key}:reset", int(self.window_seconds), str(reset_time))
            pipe.execute()

            retry_after = max(0, int(reset_time - now))
            return True, retry_after
        except redis.RedisError:
            # Fallback to memory if Redis fails
            return self._hit_memory(key)

    def _hit_memory(self, key: str) -> Tuple[bool, int]:
        """Original in-memory rate limiting implementation."""
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
