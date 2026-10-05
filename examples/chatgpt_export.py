"""Bring your own data: ChatGPT export -> scrub -> memory bank -> retrieval.

Usage (from the repo root, the directory containing `signal_action/`):

    python examples/chatgpt_export.py /path/to/conversations.json

Pipeline: parse the export -> scrub every message (PII/secrets redacted) ->
one memory per conversation -> hybrid retrieval (BM25 + embedding cosine,
RRF fused, utility-weighted) over 3 demo queries.

Embeddings here are SYNTHETIC (deterministic hash of the text, 32 dims) —
a demo prop so the example runs with zero dependencies. A deployment plugs
in a real embedding model via the query_embedding / memory embedding seam
(the lab used bge-base-en-v1.5; pgvector/HNSW path in
signal_action/retrieval/vector_store.py for scale).

Utility values below are ILLUSTRATIVE, not measured: one memory is given a
negative utility to demonstrate suppression. In production, utility is
measured per memory on a sealed holdout (see retrieval/CALIBRATION.md) —
never hand-assigned.

Export instructions:
  ChatGPT: web app -> Settings -> Data controls -> Export data -> unzip ->
           conversations.json
  Gemini:  Google Takeout (takeout.google.com) -> select "Gemini Apps" ->
           export -> map turns to (role, text, ts); see
           signal_action/capture/adapters/chatgpt.py `records_from_turns`.
"""
from __future__ import annotations

import hashlib
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_action.capture.adapters.chatgpt import parse_file
from signal_action.capture.scrubber import scrub
from signal_action.retrieval import HybridBank, tokenize

DIM = 32
EXPORT_HELP = """
Could not read the export file.

To export your ChatGPT data:
  1. Open chat.openai.com -> Settings -> Data controls -> Export data
  2. Confirm; you'll get an email with a download link
  3. Unzip and run: python examples/chatgpt_export.py /path/to/conversations.json

Gemini: Google Takeout -> select "Gemini Apps" -> export.
""".strip()


def pseudo_embedding(text: str, dim: int = DIM) -> list:
    """Deterministic demo-props embedding. NOT a real embedding model."""
    vec = [0.0] * dim
    for tok in tokenize(text):
        h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    n = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


def build_bank(records) -> tuple:
    """One memory per conversation: title + first user message, scrubbed."""
    by_conv: dict = {}
    for r in records:
        by_conv.setdefault(r.session_id, {"title": "", "first_user": ""})
        md = r.metadata or {}
        if md.get("conversation_title"):
            by_conv[r.session_id]["title"] = md["conversation_title"]
        if r.role == "user" and not by_conv[r.session_id]["first_user"]:
            by_conv[r.session_id]["first_user"] = r.content
    memories = []
    for cid, info in sorted(by_conv.items()):
        raw = f"{info['title']}: {info['first_user']}".strip(": ")
        clean = scrub(raw).text
        memories.append({
            "id": cid,
            "kind": "conversation",
            "content": clean,
            "embedding": pseudo_embedding(clean),
        })
    return memories, len(records)


def main(argv) -> int:
    if len(argv) < 2:
        print("usage: python examples/chatgpt_export.py "
              "/path/to/conversations.json")
        return 2
    path = argv[1]
    if not os.path.isfile(path):
        print(EXPORT_HELP)
        return 1

    records = parse_file(path)
    if not records:
        print("No messages parsed from the export. Is this conversations.json?")
        return 1
    memories, n_msgs = build_bank(records)
    print(f"parsed {n_msgs} messages across {len(memories)} conversations; "
          f"all scrubbed before banking.")

    # Illustrative utility: deliberately downweight one memory to demonstrate
    # suppression. Production utility is MEASURED on a sealed holdout.
    utility = {}
    if memories:
        utility[memories[0]["id"]] = -12.0  # illustrative, not measured
        for m in memories[1:]:
            utility[m["id"]] = 2.0
    bank = HybridBank(utility)

    queries = [
        "weekend project plans",
        memories[0]["content"][:60] if memories else "nothing banked",
        "what did we discuss about travel",
    ]
    for q in queries[:3]:
        print(f"\nquery: {q!r}")
        res = bank.retrieve(q, pseudo_embedding(q), memories, k=3)
        for i, r in enumerate(res, 1):
            util = utility.get(r["id"], 0.0)
            print(f"  {i}. [{r['id'][:12]}] score={r['score']:.4f} "
                  f"utility={util:+.1f}pp :: {r['content'][:80]}")

    # Explain suppression: did negative utility push a memory down?
    if memories:
        sup_id = memories[0]["id"]
        q = queries[1]
        res = bank.retrieve(q, pseudo_embedding(q), memories, k=len(memories))
        rank = next(i for i, r in enumerate(res, 1) if r["id"] == sup_id)
        if rank > 1:
            print(f"\nsuppression demo: memory {sup_id[:12]} matched the query "
                  f"closely but ranked #{rank} — its illustrative -12.0pp "
                  f"utility downweighted it. This is the mechanism the lab "
                  f"measured: memories with negative utility get suppressed "
                  f"instead of served.")
        else:
            print(f"\nsuppression demo: memory {sup_id[:12]} ranked #1 despite "
                  f"-12.0pp utility — keyword/embedding match outweighed the "
                  f"penalty on this query. Utility is a downweighting prior, "
                  f"not a veto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
