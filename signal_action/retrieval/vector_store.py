"""Vector-store seam for memory retrieval: a backend-swappable interface plus
a pgvector reference implementation.

Status: fixture-tested (interface exercised against an in-memory fake; the
pgvector reference exercised with a recording query callable — no live
Postgres exists in this package, and the reference DDL below is
UNVERIFIED ON LIVE POSTGRES: it is emitted for review, never executed here).

Design: the retrieval interface is backend-swappable — the reference
implementation takes a caller-supplied query callable and never hardcodes a
connection, driver, or credentials. Pure stdlib; no DB, no shell, no
network, no key-shaped literals.
"""

import json

__all__ = [
    "DEFAULT_DIM",
    "VectorStore",
    "PgVectorStore",
    "pgvector_migration_sql",
]

DEFAULT_DIM = 1536


def _check_vector(vec, name, dim=None):
    try:
        vals = [float(x) for x in vec]
    except TypeError:
        raise ValueError(f"{name} must be a sequence of numbers")
    if not vals:
        raise ValueError(f"{name} must not be empty")
    if dim is not None and len(vals) != dim:
        raise ValueError(
            f"{name} dim {len(vals)} != expected dim {dim}")
    return vals


def _check_k(k):
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError(f"k must be a positive integer, got {k!r}")
    return k


class VectorStore:
    """Backend-swappable vector-store interface for memory embeddings.

    Contract:
      add(memory_id, embedding, metadata=None) -> memory_id (str)
      query(query_embedding, k=6) -> list of {id, distance, metadata},
          ordered by ascending cosine distance (best first)
      delete(memory_id) -> True if a row existed, False otherwise

    "distance" is cosine distance (1 - cosine similarity); 0.0 is a perfect
    match. Implementations validate inputs; dimension expectations are the
    implementation's own (the reference pins one dim at construction).
    """

    def add(self, memory_id, embedding, metadata=None):
        """Store (or upsert) one embedding. metadata is a JSON-able dict."""
        raise NotImplementedError

    def query(self, query_embedding, k=6):
        """Top-k nearest embeddings, best first."""
        raise NotImplementedError

    def delete(self, memory_id):
        """Remove one embedding. Returns True if a row existed."""
        raise NotImplementedError


def pgvector_migration_sql(dim=DEFAULT_DIM):
    """Return the pgvector reference migration as a SQL string (extension +
    table + HNSW index). Emitted for review — this package never executes it.

    UNVERIFIED ON LIVE POSTGRES.
    """
    dim = int(dim)
    if dim < 1:
        raise ValueError(f"dim must be a positive integer, got {dim!r}")
    return f"""\
-- signal_action memory vector store: pgvector reference migration.
-- Status: UNVERIFIED ON LIVE POSTGRES. Emitted for review; never executed
-- by this package. Deployer reviews, applies, and owns the live schema.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory_embeddings (
    id         TEXT PRIMARY KEY,
    embedding  vector({dim}) NOT NULL,
    metadata   JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS memory_embeddings_embedding_hnsw
    ON memory_embeddings
    USING hnsw (embedding vector_cosine_ops);
"""


class PgVectorStore(VectorStore):
    """pgvector reference implementation of VectorStore.

    query_fn: callable(sql, params) -> rows. The deployer supplies it
    (their driver, their connection, their credentials) — this class never
    hardcodes or opens a connection.

    query() rows must be (id, distance, metadata) sequences; metadata may be
    a dict (driver-decoded JSONB) or a JSON string.

    Status: fixture-tested only — UNVERIFIED ON LIVE POSTGRES.
    """

    def __init__(self, query_fn, dim=DEFAULT_DIM):
        if not callable(query_fn):
            raise ValueError("query_fn must be a callable(sql, params) -> rows")
        dim = int(dim)
        if dim < 1:
            raise ValueError(f"dim must be a positive integer, got {dim!r}")
        self.query_fn = query_fn
        self.dim = dim

    @staticmethod
    def migration_sql(dim=DEFAULT_DIM):
        """The reference migration DDL as a string (see pgvector_migration_sql)."""
        return pgvector_migration_sql(dim)

    def add(self, memory_id, embedding, metadata=None):
        vec = _check_vector(embedding, "embedding", dim=self.dim)
        mid = str(memory_id)
        self.query_fn(
            "INSERT INTO memory_embeddings (id, embedding, metadata) "
            "VALUES (%s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET "
            "embedding = EXCLUDED.embedding, "
            "metadata = EXCLUDED.metadata",
            (mid, vec, json.dumps(metadata if metadata is not None else {})),
        )
        return mid

    def query(self, query_embedding, k=6):
        k = _check_k(k)
        vec = _check_vector(query_embedding, "query_embedding", dim=self.dim)
        rows = self.query_fn(
            "SELECT id, embedding <=> %s AS distance, metadata "
            "FROM memory_embeddings "
            "ORDER BY distance ASC "
            "LIMIT %s",
            (vec, k),
        )
        out = []
        for row in rows:
            mid, dist, meta = row[0], float(row[1]), row[2]
            if isinstance(meta, str):
                meta = json.loads(meta)
            out.append({"id": mid, "distance": dist, "metadata": meta})
        return out

    def delete(self, memory_id):
        self.query_fn(
            "DELETE FROM memory_embeddings WHERE id = %s",
            (str(memory_id),),
        )
        return True
