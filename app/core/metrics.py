from __future__ import annotations

import threading
from typing import Dict


class MetricsStore:
    """Thread-safe in-memory metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {
            "uploads": 0,
            "downloads": 0,
            "deleted": 0,
            "bytes_uploaded": 0,
        }

    def record_upload(self, size_bytes: int) -> None:
        with self._lock:
            self._counters["uploads"] += 1
            self._counters["bytes_uploaded"] += size_bytes

    def record_download(self) -> None:
        with self._lock:
            self._counters["downloads"] += 1

    def record_deletions(self, count: int) -> None:
        if count <= 0:
            return
        with self._lock:
            self._counters["deleted"] += count

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counters)


metrics = MetricsStore()
