# Examples — tap in within 5 minutes

From the repo root (the directory containing `signal_action/`):

```
python examples/quickstart.py
python examples/chatgpt_export.py /path/to/conversations.json
```

## quickstart.py — the 7-stage loop on synthetic data

Three synthetic signals go through Signal → Judgment → Proposal →
Human Decision → Action → Outcome → Learning. Each stage prints its
decision; the run ends with a learning summary. Finishes in seconds, zero
dependencies beyond the package.

Honest scoping: the Judgment step uses a **keyword heuristic as a stand-in**
for the typed decision models behind the `decide()` seam. It is a demo
prop, not a judgment engine. Scrubbing is real — every record passes
through the production scrubber before anything downstream sees it.

## chatgpt_export.py — your own conversations as a memory bank

Parses a ChatGPT `conversations.json` export, scrubs every message,
builds one memory per conversation, and runs three demo retrieval queries
showing utility-weighted ranking (BM25 + embedding cosine, RRF fused).

Embeddings are **synthetic demo props** (deterministic hash of the text).
A deployment plugs a real embedding model into the embedding seam; the
pgvector/HNSW reference lives in `signal_action/retrieval/vector_store.py`.

Utility values in this example are **illustrative, not measured** — one
memory is hand-assigned negative utility to demonstrate suppression. In
production, utility is measured per memory on a sealed holdout; see
`signal_action/retrieval/CALIBRATION.md`. Never hand-assign utility and
call it a result.

## Exporting your data

**ChatGPT:** web app → Settings → Data controls → Export data → confirm
via email → unzip → `conversations.json`.

**Gemini:** Google Takeout (takeout.google.com) → deselect all → select
"Gemini Apps" → export. Map each turn to `(role, text, ts)` (`"model"` →
`"assistant"`) and feed it to `records_from_turns()` in
`signal_action/capture/adapters/chatgpt.py` — no separate parser needed.

Both adapters are **fixture-tested only** — not yet verified against a
real export. If your export's shape differs, the parser yields records
for what it recognizes and skips the rest rather than failing.

## The closed-loop requirement

The system learns from **decisions with known outcomes**. Ten settled
decisions beat ten thousand open signals: without an outcome, a judgment
trace is trivia, not training data. Before wiring a real source, check
that you can answer "what happened?" for the decisions you log — that is
the prerequisite, not data volume.

## What remains unverified

- The ChatGPT/Gemini adapters have never run against a real export.
- The quickstart's judgment is a heuristic stand-in, not the `decide()` seam.
- Example embeddings are synthetic; swap in a real model for anything
  beyond a demo.
- Lab numbers cited in module docstrings (retrieval-v2 83.33%, utility
  findings) come from the private test program, not from this package —
  they are context, not package claims.
