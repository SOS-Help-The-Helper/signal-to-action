"""Embedding-cache tests. Synthetic fixtures only — no DB, no network, no secrets.

TTL expiry is driven by an injected fake clock (no real sleeps).

Run from the distill root: python3 -m signal_action.tests.test_cache
"""
import hashlib

from signal_action.retrieval.cache import EmbeddingCache


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def now(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def test_hit_and_miss():
    clock = FakeClock()
    c = EmbeddingCache(ttl_seconds=60.0, max_size=8, time_fn=clock.now)
    assert c.get("bridge flooded") is None  # miss before set
    c.set("bridge flooded", [0.1, 0.2, 0.3])
    hit = c.get("bridge flooded")
    assert hit == [0.1, 0.2, 0.3], f"unexpected hit: {hit}"
    assert c.get("different query") is None  # miss: different content hash
    print("cache hit/miss: OK")


def test_key_is_sha256_of_query_text():
    clock = FakeClock()
    c = EmbeddingCache(time_fn=clock.now)
    key = c.set("salt hollow", [1.0])
    expected = hashlib.sha256("salt hollow".encode("utf-8")).hexdigest()
    assert key == expected, f"key {key} != sha256 {expected}"
    print("cache key is sha256: OK")


def test_ttl_expiry():
    clock = FakeClock()
    c = EmbeddingCache(ttl_seconds=10.0, max_size=8, time_fn=clock.now)
    c.set("q", [1.0, 2.0])
    clock.advance(9.9)
    assert c.get("q") == [1.0, 2.0], "expired early"
    clock.advance(0.1)  # t = 1010.0 == set time + ttl -> expired
    assert c.get("q") is None, "did not expire at TTL"
    assert len(c) == 0, "expired entry not reclaimed"
    print("cache TTL expiry: OK")


def test_size_eviction_lru():
    clock = FakeClock()
    c = EmbeddingCache(ttl_seconds=600.0, max_size=3, time_fn=clock.now)
    c.set("a", [1.0])
    c.set("b", [2.0])
    c.set("c", [3.0])
    assert len(c) == 3
    c.get("a")  # touch "a": now "b" is least-recently-used
    c.set("d", [4.0])  # over cap -> evict "b"
    assert len(c) == 3, f"size bound violated: {len(c)}"
    assert c.get("b") is None, "LRU victim 'b' survived"
    assert c.get("a") == [1.0]
    assert c.get("c") == [3.0]
    assert c.get("d") == [4.0]
    print("cache size eviction (LRU): OK")


def test_set_stores_a_copy():
    clock = FakeClock()
    c = EmbeddingCache(time_fn=clock.now)
    vec = [0.5, 0.6]
    c.set("q", vec)
    vec.append(999.0)  # mutate caller's list after set
    assert c.get("q") == [0.5, 0.6], "cache aliased caller's list"
    print("cache stores copy: OK")


def test_clear():
    clock = FakeClock()
    c = EmbeddingCache(time_fn=clock.now)
    c.set("a", [1.0])
    c.set("b", [2.0])
    c.clear()
    assert len(c) == 0
    assert c.get("a") is None
    print("cache clear: OK")


def test_constructor_validation():
    clock = FakeClock()
    for bad in (0, -5, "60"):
        try:
            EmbeddingCache(ttl_seconds=bad, time_fn=clock.now)
        except ValueError:
            pass
        else:
            raise AssertionError(f"ttl_seconds={bad!r} did not raise ValueError")
    for bad in (0, -1, 2.5, True):
        try:
            EmbeddingCache(max_size=bad, time_fn=clock.now)
        except ValueError:
            pass
        else:
            raise AssertionError(f"max_size={bad!r} did not raise ValueError")
    print("cache constructor validation: OK")


if __name__ == "__main__":
    test_hit_and_miss()
    test_key_is_sha256_of_query_text()
    test_ttl_expiry()
    test_size_eviction_lru()
    test_set_stores_a_copy()
    test_clear()
    test_constructor_validation()
    print("\nALL CACHE TESTS PASSED")
