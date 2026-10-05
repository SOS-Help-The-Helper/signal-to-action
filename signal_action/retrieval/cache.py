"""Content-hash-keyed cache for query embeddings.

Keyed by SHA-256 of the query text so identical queries reuse the embedding
without re-encoding; TTL + max-size bound with LRU eviction so the cache
cannot grow without limit. Pure stdlib, single-process thread-safe
(threading.Lock around every operation).

Status: fixture-tested.
"""

import hashlib
import threading
import time
from collections import OrderedDict

__all__ = ["EmbeddingCache"]


def _cache_key(query_text):
    return hashlib.sha256(str(query_text).encode("utf-8")).hexdigest()


class EmbeddingCache:
    """TTL + size-bounded cache of query_text -> embedding.

    ttl_seconds: how long an entry stays valid (must be > 0).
    max_size: hard cap on entries; the least-recently-used entry is evicted
        when a new insert would exceed it (must be >= 1).
    time_fn: clock source, injectable for deterministic tests; defaults to
        time.monotonic.

    get() returns the cached embedding or None (miss or expired). set()
    stores a copy of the embedding list so later caller mutation of the
    input cannot corrupt the cache. get() returns the stored list itself —
    callers must treat the returned list as read-only.
    """

    def __init__(self, ttl_seconds=300.0, max_size=1024, time_fn=None):
        ttl = float(ttl_seconds)
        if not ttl > 0:
            raise ValueError(f"ttl_seconds must be > 0, got {ttl_seconds!r}")
        if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size < 1:
            raise ValueError(f"max_size must be an integer >= 1, got {max_size!r}")
        self.ttl_seconds = ttl
        self.max_size = max_size
        self._time = time.monotonic if time_fn is None else time_fn
        if not callable(self._time):
            raise ValueError("time_fn must be callable")
        self._lock = threading.Lock()
        self._data = OrderedDict()  # key -> (embedding, expires_at)

    def _expired(self, expires_at, now):
        return now >= expires_at

    def get(self, query_text):
        """Return the cached embedding for query_text, or None on miss/expiry."""
        key = _cache_key(query_text)
        now = self._time()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            embedding, expires_at = entry
            if self._expired(expires_at, now):
                del self._data[key]
                return None
            self._data.move_to_end(key)  # LRU touch
            return embedding

    def set(self, query_text, embedding):
        """Cache the embedding for query_text (stores a copy)."""
        try:
            vals = [float(x) for x in embedding]
        except TypeError:
            raise ValueError("embedding must be a sequence of numbers")
        key = _cache_key(query_text)
        expires_at = self._time() + self.ttl_seconds
        with self._lock:
            if key in self._data:
                del self._data[key]
            while len(self._data) >= self.max_size:
                self._data.popitem(last=False)  # evict least-recently-used
            self._data[key] = (vals, expires_at)
        return key

    def clear(self):
        """Drop all entries."""
        with self._lock:
            self._data.clear()

    def __len__(self):
        with self._lock:
            return len(self._data)
