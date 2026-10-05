"""Hybrid memory retrieval: BM25 + embedding cosine fused by Reciprocal Rank
Fusion, with utility weighting.

Status: fixture-tested.

Distilled from the lab's retrieval-v2 (decide-work/phase10/bank4.py) with all
lab wiring stripped: no database, no gate logic, no hardcoded paths, no
sys.path hacks, no phase9/phase10 imports, no CLIs. The single shipped mode is
the earned bundle from the Phase 10 ablation — hybrid RRF + utility weighting.
Excluded (did not earn their keep in ablation): MMR diversity, temporal
weighting, Clef write-time enrichment.

Lab results (NOT package claims — the package implementation is verified on
synthetic fixtures only):
  Lab (Phase 10, 178 signals / 534 paired verdicts): retrieval-v2 83.33%
  @ ~872 tok/judgment; +4.87pp vs naive top-k (p=0.0005); +1.12pp vs full
  dump (p=0.42, non-inferior).
  Utility acts primarily as a downweighting prior (lab: 61/79 memories had
  negative measured utility).

Embedding model is the deployer's choice; the lab used
@cf/baai/bge-base-en-v1.5 via Cloudflare Workers AI. The caller supplies the
query embedding vector (the lab's `_qv` seam) — this module never shells out
to any CLI or service.

Public surface:
  tokenize, ranks_desc
  BM25_K1, BM25_B, RRF_K, UTILITY_LAMBDA   (module-level tunables)
  BM25                                      (pure-python BM25 scorer)
  HybridBank                                (load_utility, retrieve)
  vector_store                              (VectorStore, PgVectorStore,
                                             pgvector_migration_sql)
  cache                                     (EmbeddingCache)
  slo                                       (LatencyTracker, DEFAULT_BUDGETS,
                                             percentile)
"""

import json
import math
import re

# ---------------------------------------------------------------------------
# Tunables (lab defaults)
# ---------------------------------------------------------------------------
BM25_K1 = 1.2
BM25_B = 0.75
RRF_K = 60
UTILITY_LAMBDA = 1.0

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text):
    """Lowercase alphanumeric tokens, matching the lab's tokenization."""
    return TOKEN_RE.findall(str(text).lower())


def ranks_desc(scores):
    """1-indexed rank per position (1 = best); ties broken by position (stable)."""
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
    ranks = [0] * len(scores)
    for rank, idx in enumerate(order, start=1):
        ranks[idx] = rank
    return ranks


def _normalize_vector(vec, name):
    try:
        vals = [float(x) for x in vec]
    except TypeError:
        raise ValueError(f"{name} must be a sequence of numbers")
    if not vals:
        raise ValueError(f"{name} must not be empty")
    norm = math.sqrt(sum(x * x for x in vals))
    if norm == 0.0:
        raise ValueError(f"{name} must not be the zero vector")
    return [x / norm for x in vals]


class BM25:
    """Pure-python BM25 (k1=1.2, b=0.75) over a fixed document set."""

    def __init__(self, documents):
        # documents: list of token lists (see tokenize())
        self.docs = list(documents)
        n = len(self.docs)
        df = {}
        for d in self.docs:
            for t in set(d):
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1.0 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.lens = [len(d) for d in self.docs]
        self.avgdl = sum(self.lens) / n if n else 1.0

    def scores(self, q_tokens):
        """BM25 score per document for the given (unique) query tokens."""
        out = [0.0] * len(self.docs)
        for t in set(q_tokens):
            idf_t = self.idf.get(t)
            if idf_t is None:
                continue
            for i, d in enumerate(self.docs):
                f = d.count(t)
                if not f:
                    continue
                denom = f + BM25_K1 * (1 - BM25_B + BM25_B * self.lens[i] / self.avgdl)
                out[i] += idf_t * (f * (BM25_K1 + 1)) / denom
        return out


class HybridBank:
    """Abstract retrieval bank: hybrid RRF (BM25 + embedding cosine) with
    per-memory utility weighting.

    Memories are plain dicts — no database, no subclassing:
        {"id": str, "kind": str, "content": str,
         "embedding": [float, ...], "utility_pp": float (optional)}

    The query embedding is supplied by the caller (the lab's `_qv` seam);
    the embedding model is the deployer's choice.
    """

    def __init__(self, utility=None):
        self.utility = {}
        if utility is not None:
            self.load_utility(utility)

    def load_utility(self, source):
        """Load per-memory utility (percentage points) from a dict or a JSON
        file path. No lab-local default path.

        Dict forms accepted:
            {memory_id: utility_pp}
            {memory_id: {"utility_pp": x, ...}}   (lab utility.json shape)
        Missing entries contribute 0.0 at retrieval time.
        """
        if isinstance(source, dict):
            items = source.items()
        else:
            with open(source, "r", encoding="utf-8") as fh:
                items = json.load(fh).items()
        util = {}
        for mid, v in items:
            if isinstance(v, dict):
                v = v.get("utility_pp", 0.0)
            util[str(mid)] = float(v)
        self.utility = util
        return dict(util)

    def retrieve(self, query_text, query_embedding, memories, k=6):
        """Return the top-k memories as a ranked list of dicts
        {id, kind, content, score, cos}.

        score = 1/(RRF_K + rank_bm25) + 1/(RRF_K + rank_emb)
                + UTILITY_LAMBDA * (utility_pp / 100)
        where ranks are 1-indexed best-first and utility_pp comes from the
        memory dict (preferred) or the bank-level utility map (else 0.0).
        cos is the cosine similarity of the query to the memory embedding.
        """
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError(f"k must be a positive integer, got {k!r}")
        if not memories:
            raise ValueError("cannot retrieve from an empty memory bank")
        qv = _normalize_vector(query_embedding, "query_embedding")
        dim = len(qv)

        ids, kinds, contents, mat = [], [], [], []
        for i, m in enumerate(memories):
            if not isinstance(m, dict):
                raise ValueError(
                    f"memory at index {i} must be a dict, got {type(m).__name__}")
            for key in ("id", "content", "embedding"):
                if key not in m:
                    raise ValueError(
                        f"memory at index {i} is missing required key {key!r}")
            emb = _normalize_vector(m["embedding"], f"memory[{i}].embedding")
            if len(emb) != dim:
                raise ValueError(
                    f"memory[{i}].embedding dim {len(emb)} != query dim {dim}")
            ids.append(m["id"])
            kinds.append(m.get("kind"))
            contents.append(str(m["content"]))
            mat.append(emb)

        n = len(ids)
        bm25 = BM25([tokenize(c) for c in contents])
        bm_scores = bm25.scores(tokenize(query_text))
        cos = [sum(a * b for a, b in zip(row, qv)) for row in mat]

        r_bm = ranks_desc(bm_scores)
        r_cos = ranks_desc(cos)

        scores = []
        for i, mid in enumerate(ids):
            rrf = 1.0 / (RRF_K + r_bm[i]) + 1.0 / (RRF_K + r_cos[i])
            pp = memories[i].get("utility_pp")
            if pp is None:
                pp = self.utility.get(str(mid), 0.0)
            scores.append(rrf + UTILITY_LAMBDA * (float(pp) / 100.0))

        order = sorted(range(n), key=lambda i: (-scores[i], i))[: min(k, n)]
        return [
            {
                "id": ids[i],
                "kind": kinds[i],
                "content": contents[i],
                "score": scores[i],
                "cos": cos[i],
            }
            for i in order
        ]


__all__ = [
    "BM25_K1",
    "BM25_B",
    "RRF_K",
    "UTILITY_LAMBDA",
    "tokenize",
    "ranks_desc",
    "BM25",
    "HybridBank",
]
