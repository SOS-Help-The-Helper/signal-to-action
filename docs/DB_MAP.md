# Data Model Map

**Status: fixture-tested.** These sketches describe the shapes the
`signal_action` package produces and consumes. They are **not** a live
schema dump and have not been verified against any production database.

**Naming rule:** adapt table and column names to your deployment. The
column *purposes* below are the contract; the identifiers are sketches.

No secrets, credentials, API keys, project refs, or live database names
appear here. Connection details plug in via config/env in deployer code.

---

## 1. Trace store — one row per scrubbed transcript record

Written by the feed pipeline (`feed.prepare_record` → a deployer
`TranscriptSink`). Read back by `provenance.rehydrate` via the
caller-injected `query_fn`. This is the verbatim source of truth:
memories never replace their sources.

```sql
CREATE TABLE trace_store (
  id            TEXT PRIMARY KEY,   -- storage id returned by the sink
                                   -- (e.g. message_id, or session_id:ts)
  platform      TEXT NOT NULL,     -- 'openclaw' | 'grokbot' | 'claude_code' | ...
  agent_id      TEXT NOT NULL,     -- which agent produced the record
  session_id    TEXT NOT NULL,     -- conversation/session grouping key
  ts            TIMESTAMPTZ NOT NULL, -- record timestamp (from NormalizedRecord.ts)
  role          TEXT NOT NULL,     -- speaker role ('user' | 'assistant' | ...)
  stream        TEXT NOT NULL,     -- 'messages' | 'reasoning'
  trace_type    TEXT NOT NULL,     -- 'agent-transcript' | 'agent-reasoning'
  intent        TEXT NOT NULL,     -- 'transcript:' || role
  message_id    TEXT,              -- platform message id (null when unavailable)
  content       TEXT NOT NULL,     -- scrubbed verbatim text, truncated to
                                   -- feed.MAX_TEXT (8000) chars
  metadata      JSONB NOT NULL DEFAULT '{}', -- platform, role, stream, ts,
                                   -- scrub_redactions ("name:mode" list),
                                   -- plus adapter-specific fields
  tags          TEXT[] NOT NULL DEFAULT '{}', -- e.g. {'transcript-capture',
                                   --  platform, stream}
  redactions    JSONB NOT NULL DEFAULT '[]',  -- (name, mode) pairs applied
                                   -- by the scrubber; audit trail
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX trace_store_session_idx ON trace_store (session_id, ts);
CREATE INDEX trace_store_stream_idx  ON trace_store (stream, ts);
```

Safety invariant (enforced in-process, not by the DB): a row is only
ever written **after** `scrub` + `assert_clean` pass. A record that fails
the leak check raises `ValueError` in `prepare_record` and never reaches
the sink. The trace store must therefore never contain unscrubbed text —
treat any row that does as a defect, not as data.

Two streams, one table: `stream = 'reasoning'` rows exist only when the
operator explicitly opted in (`--capture-thinking`, operator-owned agents
only); thinking blocks are never folded into message text.

---

## 2. Memory bank — memories, provenance pointers, validity

Consumed by `retrieval.HybridBank.retrieve` (memories are plain dicts:
`{id, kind, content, embedding, utility_pp}`). The table below is the
durable form of that dict, plus the provenance and lifecycle fields the
loops spec requires.

```sql
CREATE TABLE memory_bank (
  id               TEXT PRIMARY KEY,  -- memory id (matches retrieval dict "id")
  kind             TEXT NOT NULL,     -- memory type (e.g. rule, exemplar)
  content          TEXT NOT NULL,     -- the memory text (retrieval dict "content")
  embedding        VECTOR,            -- pgvector column; dimension MUST equal
                                      -- the embedding model's output dim
  utility_pp       DOUBLE PRECISION NOT NULL DEFAULT 0.0, -- measured utility
                                      -- in percentage points; primarily a
                                      -- downweighting prior (lab: mostly
                                      -- negative). Missing/unknown = 0.0
  source_trace_ids TEXT[] NOT NULL DEFAULT '{}', -- provenance pointers into
                                      -- trace_store.id; additive, never
                                      -- overwritten (see attach_provenance)
  status           TEXT NOT NULL DEFAULT 'provisional',
                                      -- lifecycle: 'provisional' | 'validated'
                                      -- | 'retired' (adapt to your gate)
  valid_from       TIMESTAMPTZ NOT NULL DEFAULT now(),  -- validity interval
  valid_until      TIMESTAMPTZ,        -- NULL = open-ended; decay/expiry
                                      -- required by the shared loop grammar
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX memory_bank_kind_idx   ON memory_bank (kind);
CREATE INDEX memory_bank_status_idx ON memory_bank (status);
-- Vector index (HNSW) over embedding is created by the deployer's
-- vector-store migration; see docs/DEPLOYMENT_MAP.md §3.
```

**Design notes:**

- **Non-compaction principle**: a memory never replaces its source.
  `source_trace_ids` points back to verbatim `trace_store` rows;
  `provenance.rehydrate` pulls the original excerpts on demand.
- **Checkable memories compound**: per the loops spec, a memory is only
  useful to the Memory loop if it can be verified against its sources
  (`verify_memory_against_source`); `status` tracks where a memory is
  in that lifecycle.
- **Decay/expiry required**: every memory carries a validity interval.
  Updates must be gated and must move a specified decision distribution
  measurably on a sealed holdout vs a frozen-update counterfactual, or
  the loop is defective (`loops.validate_loop` enforces this
  structurally).
- **Utility is measured, not asserted**: `utility_pp` comes from the
  Evaluation loop's override→eval-set→calibration cycle, loaded via
  `HybridBank.load_utility` (dict or JSON). The lab's gain came from
  suppressing harmful exemplars (61/79 negative), not from finding
  golden ones — size the utility pipeline accordingly.

---

## 3. Normalized signal record — the capture-layer shape

The package-internal handoff between adapters and the feed. Adapters
(`capture/adapters/*`) produce these; `feed.prepare_record` consumes
them. Not necessarily a table — it is the pre-sink shape. Included here
because deployers implementing `NormalizedRecord`-compatible adapters
need the field contract.

```sql
-- Conceptual shape (usually a dataclass, not a table):
--   platform    TEXT  -- adapter name
--   agent_id    TEXT  -- producing agent
--   session_id  TEXT  -- conversation/session grouping
--   ts          TEXT  -- ISO timestamp (string at this layer)
--   role        TEXT  -- 'user' | 'assistant' | ...
--   stream      TEXT  -- 'messages' | 'reasoning'
--   content     TEXT  -- RAW text (unscrubbed; scrubbed only in prepare_record)
--   message_id  TEXT  -- platform message id
--   metadata    JSON  -- adapter-specific fields
```

Note: `content` is **unscrubbed** at this layer by design — scrubbing
happens exactly once, in `prepare_record`, immediately before the sink.
Never persist a `NormalizedRecord` directly.

---

## 4. How the three relate

```
adapters ──NormalizedRecord──▶ feed.prepare_record ──ScrubbedRecord──▶ trace_store
     (raw text)              (scrub + assert_clean)      (verbatim source of truth)
                                                                    │
memory_bank ◀── source_trace_ids ── attach_provenance ───────────────┘
     │  (kind, content, embedding, utility_pp, status, validity)
     │
     ▼
HybridBank.retrieve(query_text, query_embedding, memories, k)
     │
     ▼
rehydrate(trace_ids, query_fn) ──▶ trace_store (verbatim excerpts back)
```

- The **trace store** is append-only in practice: transcript rows are
  never edited (a correction is a new row; provenance points at ids).
- The **memory bank** is the mutable layer: utility updates, status
  transitions, and validity intervals change here, gated by the
  Evaluation/Memory loops.
- **Rehydration** closes the loop: any memory can be verified against
  the verbatim rows it was derived from. A memory whose sources cannot
  be rehydrated is unverifiable — the caller decides what that means.
