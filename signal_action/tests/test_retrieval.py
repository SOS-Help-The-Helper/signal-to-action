"""Retrieval tests. Synthetic fixtures only — no DB, no network, no secrets.

Run from the distill root: python3 -m signal_action.tests.test_retrieval
"""
import os
import random
import tempfile

from signal_action.retrieval import (
    BM25,
    HybridBank,
    ranks_desc,
    tokenize,
)


def _vec(rng, dim=16):
    v = [rng.gauss(0, 1) for _ in range(dim)]
    n = sum(x * x for x in v) ** 0.5
    return [x / n for x in v]


def make_bank():
    rng = random.Random(42)
    return [
        {"id": "m-bridge", "kind": "exemplar",
         "content": "Salt Hollow bridge flooded, water over the deck",
         "embedding": _vec(rng), "utility_pp": 0.0},
        {"id": "m-river", "kind": "exemplar",
         "content": "river gauge readings at high water near the crossing",
         "embedding": _vec(rng), "utility_pp": 0.0},
        {"id": "m-shelter", "kind": "exemplar",
         "content": "shelter open at the community hall tonight",
         "embedding": _vec(rng), "utility_pp": 0.0},
        {"id": "m-road", "kind": "exemplar",
         "content": "road closure on highway 9, detour marked",
         "embedding": _vec(rng), "utility_pp": 0.0},
        {"id": "m-aid", "kind": "exemplar",
         "content": "first aid supplies available at the church",
         "embedding": _vec(rng), "utility_pp": 0.0},
        {"id": "m-veg", "kind": "exemplar",
         "content": "garden veggies to share, looking for canning jars",
         "embedding": _vec(rng), "utility_pp": 0.0},
    ]


def _query_vec():
    # independent seed from the bank fixture: never collides with a
    # memory embedding by construction of the test
    return _vec(random.Random(7))


def test_tokenize():
    assert tokenize("Salt Hollow BRIDGE-2") == ["salt", "hollow", "bridge", "2"]
    assert tokenize("") == []
    print("tokenize: OK")


def test_ranks_desc():
    assert ranks_desc([0.1, 0.9, 0.5]) == [3, 1, 2]
    # ties broken by position (stable)
    assert ranks_desc([0.5, 0.5, 0.9]) == [2, 3, 1]
    print("ranks_desc: OK")


def test_bm25_prefers_keyword_match():
    docs = [tokenize("salt hollow bridge flooded"),
            tokenize("garden veggies canning jars")]
    bm = BM25(docs)
    s = bm.scores(tokenize("bridge flooded salt hollow"))
    assert s[0] > s[1] and s[1] == 0.0, f"unexpected BM25: {s}"
    print("bm25 keyword match: OK")


def test_hybrid_returns_ranked_k():
    bank = make_bank()
    q = _query_vec()
    bank[0]["embedding"] = list(q)  # exact cosine match on the top memory
    b = HybridBank()
    res = b.retrieve("bridge flooded salt hollow", q, bank, k=3)
    assert len(res) == 3, f"expected 3, got {len(res)}"
    assert res[0]["id"] == "m-bridge", f"top hit wrong: {res[0]['id']}"
    for r in res:
        assert set(r) >= {"id", "kind", "content", "score", "cos"}, r.keys()
    scores = [r["score"] for r in res]
    assert scores == sorted(scores, reverse=True), "not ranked desc"
    assert abs(res[0]["cos"] - 1.0) < 1e-9, f"cos should be 1.0, got {res[0]['cos']}"
    print("hybrid ranked k: OK")


def test_utility_moves_ranking():
    rng = random.Random(42)
    q = _vec(rng)
    e2 = [0.0] * 16
    e2[1] = 1.0  # orthogonal to nothing in particular; just distinct
    bank = [
        {"id": "m-a", "kind": "exemplar",
         "content": "Salt Hollow bridge flooded, water over the deck",
         "embedding": list(q)},
        {"id": "m-b", "kind": "exemplar",
         "content": "garden veggies to share, looking for canning jars",
         "embedding": e2},
        {"id": "m-c", "kind": "exemplar",
         "content": "bridge inspection scheduled for tuesday morning",
         "embedding": _vec(rng)},
        {"id": "m-d", "kind": "exemplar",
         "content": "shelter open at the community hall tonight",
         "embedding": _vec(rng)},
    ]
    query = "bridge flooded salt hollow"
    plain = HybridBank()
    base = plain.retrieve(query, q, bank, k=4)
    assert base[0]["id"] == "m-a", f"baseline top should be m-a, got {base[0]['id']}"

    boosted = HybridBank()
    boosted.load_utility({"m-b": 10.0})
    with_u = boosted.retrieve(query, q, bank, k=4)
    assert with_u[0]["id"] == "m-b", (
        f"utility +10pp should move m-b to top, got {with_u[0]['id']}")
    # and the score moved by exactly the utility term
    b_plain = next(r for r in base if r["id"] == "m-b")
    b_util = next(r for r in with_u if r["id"] == "m-b")
    assert abs((b_util["score"] - b_plain["score"]) - 0.10) < 1e-9, (
        f"utility term mismatch: {b_util['score'] - b_plain['score']}")
    print("utility moves ranking: OK")


def test_deterministic_across_runs():
    bank = make_bank()
    q = _query_vec()
    bank[0]["embedding"] = list(q)
    b = HybridBank()
    r1 = b.retrieve("bridge flooded", q, bank, k=6)
    r2 = b.retrieve("bridge flooded", q, bank, k=6)
    assert [r["id"] for r in r1] == [r["id"] for r in r2]
    assert [r["score"] for r in r1] == [r["score"] for r in r2]
    print("deterministic: OK")


def test_invalid_k_raises():
    bank = make_bank()
    q = _query_vec()
    bank[0]["embedding"] = list(q)
    b = HybridBank()
    for bad in (0, -1, "6", 2.5, True):
        try:
            b.retrieve("bridge", q, bank, k=bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"k={bad!r} did not raise ValueError")
    print("invalid k raises: OK")


def test_empty_bank_raises():
    b = HybridBank()
    try:
        b.retrieve("bridge", [1.0, 0.0], [], k=6)
    except ValueError:
        pass
    else:
        raise AssertionError("empty bank did not raise ValueError")
    print("empty bank raises: OK")


def test_dim_mismatch_raises():
    bank = make_bank()
    b = HybridBank()
    try:
        b.retrieve("bridge", [1.0, 0.0], bank, k=6)  # dim 2 vs dim 16
    except ValueError:
        pass
    else:
        raise AssertionError("dim mismatch did not raise ValueError")
    print("dim mismatch raises: OK")


def test_load_utility_dict_and_path():
    bank = make_bank()
    q = _query_vec()
    bank[0]["embedding"] = list(q)
    query = "bridge flooded salt hollow"

    b1 = HybridBank()
    u = b1.load_utility({"m-bridge": -5.0})
    assert u == {"m-bridge": -5.0}
    r1 = b1.retrieve(query, q, bank, k=6)

    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "utility.json")
        # lab shape: {id: {utility_pp, ...}}
        with open(p, "w", encoding="utf-8") as fh:
            fh.write('{"m-bridge": {"utility_pp": -5.0, "kind": "exemplar", "n_pairs": 3}}')
        b2 = HybridBank()
        u2 = b2.load_utility(p)
        assert u2 == {"m-bridge": -5.0}
        r2 = b2.retrieve(query, q, bank, k=6)

    assert [r["id"] for r in r1] == [r["id"] for r in r2]
    assert [r["score"] for r in r1] == [r["score"] for r in r2]
    print("load_utility dict + path: OK")


def test_per_memory_utility_pp_beats_bank_map():
    rng = random.Random(42)
    q = _vec(rng)
    e2 = [0.0] * 16
    e2[1] = 1.0
    bank = [
        {"id": "m-a", "kind": "exemplar",
         "content": "Salt Hollow bridge flooded, water over the deck",
         "embedding": list(q)},
        {"id": "m-b", "kind": "exemplar",
         "content": "garden veggies to share, looking for canning jars",
         "embedding": e2, "utility_pp": 10.0},  # per-memory wins
    ]
    b = HybridBank({"m-b": -50.0})  # bank map disagrees
    res = b.retrieve("bridge flooded salt hollow", q, bank, k=2)
    assert res[0]["id"] == "m-b", (
        f"per-memory utility_pp should take precedence, got {res[0]['id']}")
    print("per-memory utility precedence: OK")


if __name__ == "__main__":
    test_tokenize()
    test_ranks_desc()
    test_bm25_prefers_keyword_match()
    test_hybrid_returns_ranked_k()
    test_utility_moves_ranking()
    test_deterministic_across_runs()
    test_invalid_k_raises()
    test_empty_bank_raises()
    test_dim_mismatch_raises()
    test_load_utility_dict_and_path()
    test_per_memory_utility_pp_beats_bank_map()
    print("\nALL RETRIEVAL TESTS PASSED")
