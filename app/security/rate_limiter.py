import threading
import time
from collections import defaultdict, deque
from functools import lru_cache

from core.config import get_settings


class RateLimiter:
    """A sliding-window rate limiter, in-memory, keyed by an arbitrary string
    (e.g. a Streamlit session id).

    Scaling note: this is process-local. It correctly limits a single running
    process, but if this app is ever deployed as multiple replicas behind a
    load balancer, each replica gets its own independent counters and the
    effective limit multiplies by replica count. Scaling past one process
    requires moving the counters to a shared store (e.g. Redis INCR+EXPIRE,
    or a sorted set per key) instead of this in-memory dict — same interface,
    different backend.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True

    def seconds_until_next_slot(self, key: str) -> float:
        with self._lock:
            hits = self._hits[key]
            if len(hits) < self.max_requests:
                return 0.0
            return max(0.0, self.window_seconds - (time.monotonic() - hits[0]))


@lru_cache
def get_rate_limiter() -> RateLimiter:
    # lru_cache: one shared RateLimiter instance for the whole process, so
    # every Streamlit session's hits land in the same counters.
    settings = get_settings()
    return RateLimiter(
        max_requests=settings.rate_limit_max_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
