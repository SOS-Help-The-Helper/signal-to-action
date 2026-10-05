"""Vector-store tests. Synthetic fixtures only — no DB, no network, no secrets.

Interface tests run against an in-memory fake VectorStore; the pgvector
reference is exercised with a recording query callable (its DDL is only
ever emitted as a string, never executed).

Run from the distill root: python3 -m signal_action.tests.test_vector_store
"""
import math

from signal_action.retrieval.vector_store import (
    PgVectorStore,
    VectorStore,
    pgvector_migration_sql,
)


def _cos_dist(a, b):
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return 1.0 - sum(x * y for x, y in zip(a, b)) / (na * nb)


class FakeVectorStore(VectorStore):
    """In-memory VectorStore: the interface contract, nothing else."""

    def __init__(self):
        self._rows = {}

    def add(self, memory_id, embedding, metadata=None):
        vals = [float(x) for x in embedding]
        if not vals:
            raise ValueError("embedding must not be empty")
        mid = str(memory_id)
        self._rows[mid] = (vals, dict(metadata) if metadata else {})
        return mid

    def query(self, query_embedding, k=6):
        q = [float(x) for x in query_embedding]
        ranked = sorted(
            self._rows.items(),
            key=lambda kv: (_cos_dist(q, kv[1][0]), kv[0]),
        )
        return [
            {"id": mid, "distance": _cos_dist(q, vec), "metadata": meta}
            for mid, (vec, meta) in ranked[:k]
        ]

    def delete(self, memory_id):
        return self._rows.pop(str(memory_id), None) is not None


def _three_vectors():
    return {
        "m-a": [1.0, 0.0, 0.0],
        "m-b": [0.0, 1.0, 0.0],
        "m-c": [0.0, 0.0, 1.0],
    }


def test_interface_add_query_round_trip():
    store = FakeVectorStore()
    assert isinstance(store, VectorStore)
    for mid, vec in _three_vectors().items():
        assert store.add(mid, vec, {"kind": "exemplar"}) == mid
    # exact match on m-b's embedding: distance 0, ranked first
    res = store.query([0.0, 1.0, 0.0], k=3)
    assert len(res) == 3
    assert res[0]["id"] == "m-b"
    assert abs(res[0]["distance"] - 0.0) < 1e-12
    assert res[0]["metadata"] == {"kind": "exemplar"}
    dists = [r["distance"] for r in res]
    assert dists == sorted(dists), "not ordered by ascending distance"
    for r in res:
        assert set(r) >= {"id", "distance", "metadata"}, r.keys()
    print("interface add/query round-trip: OK")


def test_interface_query_k_limit():
    store = FakeVectorStore()
    for mid, vec in _three_vectors().items():
        store.add(mid, vec)
    res = store.query([1.0, 0.0, 0.0], k=2)
    assert len(res) == 2
    assert res[0]["id"] == "m-a"
    print("interface k limit: OK")


def test_interface_delete():
    store = FakeVectorStore()
    for mid, vec in _three_vectors().items():
        store.add(mid, vec)
    assert store.delete("m-b") is True
    ids = [r["id"] for r in store.query([0.0, 1.0, 0.0], k=3)]
    assert "m-b" not in ids, f"deleted row still returned: {ids}"
    assert store.delete("m-b") is False  # already gone
    assert store.delete("nope") is False
    print("interface delete: OK")


def test_interface_rejects_empty_embedding():
    store = FakeVectorStore()
    try:
        store.add("m-x", [])
    except ValueError:
        pass
    else:
        raise AssertionError("empty embedding did not raise ValueError")
    print("interface empty embedding raises: OK")


class RecordingQuery:
    """Fake query_fn: records (sql, params), replays canned rows."""

    def __init__(self):
        self.calls = []
        self.rows = []

    def __call__(self, sql, params):
        self.calls.append((sql, params))
        return list(self.rows)


def test_pgvector_migration_contains_hnsw_ddl():
    sql = pgvector_migration_sql()
    assert "CREATE EXTENSION" in sql and "vector" in sql
    assert "CREATE TABLE" in sql and "memory_embeddings" in sql
    assert "USING hnsw" in sql, "migration missing HNSW index DDL"
    assert "vector_cosine_ops" in sql, "migration missing vector_cosine_ops"
    # class-level accessor emits the same DDL
    assert PgVectorStore.migration_sql() == sql
    # dim is honored
    assert "vector(768)" in pgvector_migration_sql(dim=768)
    print("pgvector migration HNSW DDL: OK")


def test_pgvector_add_emits_upsert():
    rec = RecordingQuery()
    store = PgVectorStore(rec, dim=3)
    assert store.add("m-a", [1.0, 0.0, 0.0], {"kind": "exemplar"}) == "m-a"
    sql, params = rec.calls[0]
    assert "INSERT INTO memory_embeddings" in sql
    assert "ON CONFLICT (id)" in sql
    assert params[0] == "m-a"
    assert params[1] == [1.0, 0.0, 0.0]
    assert '"kind": "exemplar"' in params[2]
    print("pgvector add emits upsert: OK")


def test_pgvector_query_emits_cosine_order():
    rec = RecordingQuery()
    rec.rows = [("m-b", 0.0, {"kind": "exemplar"}),
                ("m-a", 0.5, '{"kind": "note"}')]
    store = PgVectorStore(rec, dim=3)
    res = store.query([0.0, 1.0, 0.0], k=2)
    sql, params = rec.calls[0]
    assert "embedding <=> %s" in sql, f"missing cosine-distance op: {sql}"
    assert "ORDER BY distance ASC" in sql
    assert "LIMIT %s" in sql
    assert params == ([0.0, 1.0, 0.0], 2)
    assert res[0] == {"id": "m-b", "distance": 0.0,
                      "metadata": {"kind": "exemplar"}}
    # JSON-string metadata is decoded too
    assert res[1]["metadata"] == {"kind": "note"}
    print("pgvector query emits cosine order: OK")


def test_pgvector_delete_emits_delete():
    rec = RecordingQuery()
    store = PgVectorStore(rec, dim=3)
    store.delete("m-a")
    sql, params = rec.calls[0]
    assert sql.strip().startswith("DELETE FROM memory_embeddings")
    assert params == ("m-a",)
    print("pgvector delete emits delete: OK")


def test_pgvector_rejects_bad_dim_and_query_fn():
    for bad in (None, "x"):
        try:
            PgVectorStore(bad, dim=3)
        except ValueError:
            pass
        else:
            raise AssertionError(f"query_fn={bad!r} did not raise ValueError")
    rec = RecordingQuery()
    for bad_dim in (0, -1):
        try:
            PgVectorStore(rec, dim=bad_dim)
        except ValueError:
            pass
        else:
            raise AssertionError(f"dim={bad_dim} did not raise ValueError")
    store = PgVectorStore(rec, dim=3)
    for bad_vec in ([1.0, 0.0], "nope", []):
        try:
            store.add("m-x", bad_vec)
        except ValueError:
            pass
        else:
            raise AssertionError(f"embedding={bad_vec!r} did not raise ValueError")
    print("pgvector validation: OK")


def test_pgvector_never_hardcodes_connection():
    # the reference holds only the caller-supplied callable — no driver
    # import, no DSN/URL attribute, no connection state of its own
    rec = RecordingQuery()
    store = PgVectorStore(rec, dim=3)
    assert store.query_fn is rec
    src_attrs = set(vars(store))
    assert src_attrs <= {"query_fn", "dim"}, src_attrs
    print("pgvector no hardcoded connection: OK")


if __name__ == "__main__":
    test_interface_add_query_round_trip()
    test_interface_query_k_limit()
    test_interface_delete()
    test_interface_rejects_empty_embedding()
    test_pgvector_migration_contains_hnsw_ddl()
    test_pgvector_add_emits_upsert()
    test_pgvector_query_emits_cosine_order()
    test_pgvector_delete_emits_delete()
    test_pgvector_rejects_bad_dim_and_query_fn()
    test_pgvector_never_hardcodes_connection()
    print("\nALL VECTOR STORE TESTS PASSED")
