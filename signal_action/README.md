# signal_action — the open Signal-to-Action framework package

Distilled from the Signal-to-Action research program (Oct 2026). This is the
open framework: the loop, the capture layer, the memory plumbing. The learning
substrate — tuned parameters, calibration corpora, production memory banks —
stays private. That is the open-core split, stated plainly.

**Status: fixture-tested.** Lab baselines: capture 8/8 end-to-end + 10/10
reasoning-stream (distill: 13/13 + 12/12); retrieval-v2 lab experiment
83.33% @ ~872 tok/judgment on the 178-signal holdout (distill: 11/11 on
synthetic fixtures); loops spec 10/10. Nothing here has been verified against
a live system — every module docstring says so, and so does this file.

## The paper

**Signal-to-Action: The Framework** — the coordination problem and solution,
with the full test program and the failures kept in the record.

## Layout

```
signal_action/
  capture/
    adapters/      base (NormalizedRecord + BaseAdapter), openclaw,
                   claude_code, muse_db
    scrubber.py    ordered PII/secret redaction + assert_clean leak check
    sinks.py       TranscriptSink interface + bundled JsonlSink
    feed.py        scrub -> leak-check -> sink pipeline, filter_stream, CLI
  provenance/
    provenance.py  attach_provenance / rehydrate / verify_memory_against_source
  retrieval/
    __init__.py    hybrid BM25 + embedding-cosine fusion (RRF) + utility
                   weighting; HybridBank.retrieve(query_text,
                   query_embedding, memories, k=6); load_utility()
  loops/
    __init__.py    the framework spec as code: 7-stage outer loop, four
                   inner loops, four lanes, gate rules, validate_loop(),
                   language + naming constants
  tests/           ported lab suite (synthetic fixtures only)
```

## Capture + provenance (distilled)

Two streams, as in the lab: `messages` (verbatim conversation, all agents)
and `reasoning` (opt-in thinking capture, `--capture-thinking`; operator-owned
agents only — thinking blocks are never folded into message text).

## Wiring your own backends

This distill ships **no production persistence or querying** by design.
Two injection points:

- **Feed writes:** pass a `TranscriptSink` to `feed_records(records,
  sink=..., dry_run=False)`. The only bundled sink is `JsonlSink` (local
  file, good for integration). Subclass `TranscriptSink` for
  Supabase/Postgres/HTTP.
- **Rehydration reads:** `rehydrate(trace_ids, query_fn)` takes a required
  injectable `query_fn(trace_ids) -> {trace_id: excerpt}`. There is
  deliberately no default — the lab's default shelled out to a Supabase CLI
  bound to a specific project.

Safety invariant, kept: `prepare_record` scrubs and runs `assert_clean`
*before* any sink call. A record that fails the leak check raises
`ValueError` and is never written.

## API changes vs the lab

- `rehydrate()` no longer stuffs a magic `"_missing"` key into the excerpts
  dict; it returns `{"excerpts": {...}, "missing": [...]}`.
- `feed_records()` no longer builds Supabase INSERT SQL or shells out; it
  returns prepared `ScrubbedRecord`s on dry-run and writes through a
  `TranscriptSink` otherwise (write without a sink raises `ValueError`).
- The CLI's `--write` now requires `--jsonl-out <path>`; there is no
  `--write`-to-database path in this distribution.

## Stripped (do not re-add)

`attach_to_bank_memory`, `rehydrate_for_memory`, `_bank_sql` — the lab's
bank-level wiring hardcoded a **production** database project reference
(despite a stale "TEST" comment). Bank/memory-DB wiring belongs in
deployer code with explicit credentials, never in a public package.

## Blocked: Instinct adapter

No Instinct adapter ships. Instinct is a hosted iMessage agent with no
documented programmatic transcript export as of 2026-10-05. The lab carried
a dead stub whose only behavior was a loud `NotImplementedError`; this
distill excludes it entirely rather than ship a dead import path. Capture
options (export API request, on-device iMessage store, manual paste-in)
remain future work.

## Retrieval (distilled)

Hybrid BM25 + embedding-cosine retrieval fused with Reciprocal Rank Fusion,
plus utility weighting — the exact bundle that earned its keep in the Phase
10 lab ablation (+4.87pp vs naive top-k, p=0.0005; lab numbers cited, not
claimed for this package). MMR diversity, temporal weighting, and Clef
enrichment did not earn their keep and are not included.

- `HybridBank.retrieve(query_text, query_embedding, memories, k=6)` —
  memories are plain dicts `{id, kind, content, embedding, utility_pp}`;
  the query embedding is caller-supplied (the embedding model is the
  deployer's choice; the lab used `@cf/baai/bge-base-en-v1.5`). Pure stdlib,
  no dependencies, no database, no network.
- Utility acts primarily as a downweighting prior (lab: 61/79 memories had
  negative measured utility — the gain came from suppressing harmful
  exemplars, not finding golden ones).

## Loops (distilled spec)

The framework as code, from the canonical loops document:

- **Outer loop** — the 7 stages in order: Signal → Judgment → Proposal →
  Human Decision → Action → Outcome → Learning, each with its contract.
- **Inner loops** — Coordination ("maintains the commitment record":
  Match→Route→Commit→Track→Learn), Memory ("maintains the decision rules":
  Outcome→Memory→Judgment), Trust ("maintains the routing weights":
  Evidence→Score→Routing weight), Evaluation ("maintains the calibration
  set": Override→Eval set→Calibration).
- **Shared grammar** — Observe → Update persistent state → Steer future
  decisions, with the falsifiable bar: updates must be gated, carry
  decay/expiry, and move a specified decision distribution measurably on a
  sealed holdout vs a frozen-update counterfactual. `validate_loop()`
  enforces this structurally.
- **Lanes** — Sorting (decision models), Synthesis (LLMs), Guarantee
  (deterministic: IDs, ledger, math), Decision (humans at the gate).
- **Language + naming constants** — requests/resources/helpers (never
  "needs"/"offers" as nouns, never "volunteers"); never "survivor" for
  people getting help; Signal-to-Action = framework, Relay = engine,
  Judgment = user-facing stage, TypeSafe Jev = vendor model, SOS scorer =
  internal deterministic scorer.

Inner-loop publishability verdicts live in the paper, not here.

## Tests

Plain `python3`, no dependencies:

```sh
python3 -m signal_action.tests.test_end_to_end
python3 -m signal_action.tests.test_reasoning_stream
python3 -m signal_action.tests.test_retrieval
python3 -m signal_action.tests.test_loops
```

46 tests, all passing on synthetic fixtures.

## Key-literal rule

See `tests/README.md`: key-shaped secrets are runtime-built in tests, never
written as literals. Same discipline applies to any future fixture or
source edit in this package.
