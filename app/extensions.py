import threading
import time

from flask_wtf import CSRFProtect

csrf = CSRFProtect()


class LoginLimiter:
    """Rate limit login sederhana in-memory (per proses).
    Untuk deploy multi-instance, ganti dengan Flask-Limiter + Redis."""

    def __init__(self, max_attempts=5, window_seconds=300):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._hits = {}
        self._lock = threading.Lock()

    def _recent(self, key, now):
        return [t for t in self._hits.get(key, []) if now - t < self.window]

    def blocked(self, key):
        with self._lock:
            hits = self._recent(key, time.monotonic())
            self._hits[key] = hits
            return len(hits) >= self.max_attempts

    def hit(self, key):
        with self._lock:
            now = time.monotonic()
            self._hits[key] = self._recent(key, now) + [now]

    def reset(self, key):
        with self._lock:
            self._hits.pop(key, None)


login_limiter = LoginLimiter()
