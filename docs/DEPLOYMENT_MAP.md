# Deployment Map

**Status: fixture-tested.** The `signal_action` package is verified on
synthetic fixtures (46/46 tests green). Nothing in this map has been
verified against a live deployment — treat every sizing and latency
number as a starting assumption to re-measure in your environment, not
as a guarantee.

No secrets, credentials, API keys, project refs, or live database names
appear here by design. All deployment values plug in via config/env;
this document names the config knobs, never the values.

---

## 1. Components

| Component | What it is | Package entry point |
|---|---|---|
| Capture adapters | Platform-specific readers that normalize raw session data into `NormalizedRecord`s (messages stream; reasoning stream opt-in via `--capture-thinking`) | `signal_action.capture.adapters` (`openclaw`, `grokbot`, `claude_code`) |
| Scrub gate | Ordered PII/secret redaction + `assert_clean` leak check. Sits **before** every write; a failing record raises `ValueError` and is never persisted | `signal_action.capture.scrubber`, applied by `feed.prepare_record` |
| Feed / sinks | Scrub → leak-check → sink pipeline. Only bundled sink is `JsonlSink` (local file). Production backends are deployer-implemented via the `TranscriptSink` interface (`write(ScrubbedRecord) -> str`) | `signal_action.capture.feed`, `signal_action.capture.sinks` |
| Provenance | Pure functions: `attach_provenance` (additive, deduped `source_trace_ids` on a memory), `rehydrate` (verbatim excerpt lookup by trace id via caller-injected `query_fn` — no default), `verify_memory_against_source` | `signal_action.provenance.provenance` |
| Retrieval | Hybrid BM25 + embedding-cosine fused by Reciprocal Rank Fusion, plus utility weighting. `HybridBank.retrieve(query_text, query_embedding, memories, k=6)`. Pure stdlib: no DB, no network. The query embedding is caller-supplied — the embedding model is the deployer's choice (lab used `@cf/baai/bge-base-en-v1.5`) | `signal_action.retrieval` |
| Vector store | **Reference implementation only.** The shipped `HybridBank` operates on in-memory dicts; at scale, deployers swap the document set for a vector store (pgvector chosen in the lab) behind a retrieval interface kept backend-swappable | Deployer code (see §5) |
| Cache | Caller-owned result cache in front of retrieval (not shipped). Typical key: hash of (query text, embedding version, k, bank revision) → ranked result | Deployer code (see §6) |
| SLO instrumentation | Not shipped — deployer-owned. Suggested metrics in §7 | Deployer code |
| Loop contracts | The 7-stage outer loop, four inner loops, four lanes, gate rules, and naming/language constants as code (`validate_loop()`) | `signal_action.loops` |

Tunables (module-level, lab defaults): `BM25_K1=1.2`, `BM25_B=0.75`,
`RRF_K=60`, `UTILITY_LAMBDA=1.0`. Feed truncation: `feed.MAX_TEXT=8000`
characters per record.

---

## 2. What runs where

**Per-process (library, no host required):**

- Capture adapters + CLI (`python3 -m signal_action.capture.feed`)
- Scrub gate (`scrub`/`assert_clean`) — must run in the same process as
  the feed, before any sink write
- `JsonlSink` for integration/local staging
- `HybridBank` retrieval over an in-memory memory list — suitable for
  banks up to low tens of thousands of memories on a single host
- Provenance pure functions; `rehydrate` needs a caller-supplied
  `query_fn`, which is typically a DB/HTTP call and therefore usually
  runs in the host process

**Hosted (deployer-provisioned):**

- Trace store: Postgres (or equivalent) receiving `ScrubbedRecord`s via a
  deployer-implemented `TranscriptSink`. Owns the verbatim transcript
  text that `rehydrate` reads back
- Memory bank: Postgres table(s) for memories, `source_trace_ids`,
  utility values, validity intervals (see `docs/DB_MAP.md`)
- Vector store: pgvector on the memory bank database, co-locating vectors
  with gate metadata so "similar AND validated/provisional" is one query
- Embedding service for producing query/memory embeddings
  (deployer's model choice; dimension must match the pgvector column)

The package intentionally has **no network calls and no credential
handling**. Every hosted dependency is injected through the two seams:
`TranscriptSink` (writes) and `rehydrate`'s `query_fn` (reads).

---

## 3. The pgvector migration

The HNSW index DDL lives in the deployer's vector-store reference code,
not in this package. Applying it follows the standard pattern:

1. **Enable the extension** in the memory-bank database
   (`CREATE EXTENSION IF NOT EXISTS vector;` — run once per database).
2. **Add the embedding column** to the memory table with the dimension
   matching your embedding model (the lab's model produced 768 dims;
   your dimension is a config knob — it must equal the model output,
   or inserts will fail).
3. **Create the HNSW index** over the embedding column with the model's
   distance opclass. Config knobs: construction parameters
   (`m`, `ef_construction`) trade build time / index size for recall;
   query-time `ef_search` trades latency for recall.
4. **Backfill** existing memory rows: generate embeddings for each
   memory's content with the same model and dimension, then insert.
5. **Gate-metadata co-location**: because vectors share the table with
   `kind`, status flags, and validity intervals (see `docs/DB_MAP.md`),
   the hot query is a single `WHERE` on metadata + `ORDER BY embedding
   <-> query` with a `LIMIT` — no join to a separate store.

Migration tooling is deployer choice (raw `psql`, sqitch, alembic,
framework migrations). Version the migration with the embedding model:
changing models means a new column or a full re-backfill, since
dimensions and distances are not comparable across models.

---

## 4. Cache sizing guidance

The retrieval path is: caller embeds query → hybrid RRF over the bank →
top-k memories. Two cache layers are worth considering; both are
deployer-owned.

**Result cache (hot path).**
Key: hash of (query text, embedding-model version, `k`, bank revision).
Value: the ranked result list.

- **TTL**: bound by bank churn. If memories/utility values change daily,
  a TTL in the hours range is the sane starting point; if the bank is
  effectively static between scheduled rebuilds, TTL can cover the
  rebuild interval. Include the bank revision in the key so a rebuild
  naturally invalidates.
- **Size bound**: each entry is roughly `k × (excerpt size + overhead)`.
  For k=6 and ~1–2 KB excerpts, entries are ~10–15 KB. A 10k-entry cache
  is therefore ~100–150 MB. Size the cache as
  `entries × k × mean_excerpt_bytes`, and cap entries with an LRU eviction.

**Embedding cache (optional).**
Query embeddings for repeated or template queries can be cached by
query-text hash. TTL is tied to the embedding-model version: any model
change invalidates the whole cache.

**How to think about it per workload:**

- Low-traffic / small bank (< 10k memories): `HybridBank` in-process with
  no cache is usually fine; the result cache earns its keep only if the
  same queries repeat.
- High-traffic / large bank: pgvector-backed retrieval + result cache;
  size the cache from measured query repetition (log the key-hit rate
  for a week before committing to a size).
- Write-heavy bank (utility values updating continuously from the
  Evaluation loop): prefer short TTLs or revision-keyed invalidation
  over large caches — stale utility weights silently skew ranking.

---

## 5. SLO configuration

The package ships no instrumentation; SLOs are caller-configured.
Budgets exist for each stage — set them in your config, alert on them
from your observability stack.

| Budget | Suggested default | What it guards |
|---|---|---|
| Retrieval latency (p95) | 500 ms in-process; 2 s with pgvector + remote embedding call | Judgment-stage responsiveness |
| Tokens per judgment | 1,000 (see scaling notes below) | Cost containment per decision |
| Sink write success rate | ≥ 99.9% | No transcript loss at the scrub gate output |
| Scrub-gate leak rate | 0 (any `assert_clean` failure pages) | PII/secret leak prevention |
| Rehydration miss rate | < 1% of requested trace ids | Provenance verifiability |
| Cache hit rate (if cached) | ≥ 50% before sizing up the cache | Cache ROI |
| Embedding-model drift | pinned version; alert on any change | Vector comparability |

All defaults above are starting points, documented here so a deployer
can see them in one place. Override every one of them from config or
env; the framework itself reads none of these.

---

## 6. Scaling notes (lab-measured, not guarantees)

From the lab's retrieval experiments (Phase 9/10, cited in
`signal_action/retrieval/__init__.py` and the paper — **lab numbers,
not package claims**):

- **Full-dump baseline**: dumping the whole memory bank into the prompt
  costs ~43 tokens per memory — roughly 24× the cost of retrieval at
  500 exemplars. Cost grows linearly with bank size.
- **Retrieval**: flat at ~900 tokens per judgment regardless of bank
  size (lab measured ~872 tok/judgment on the 178-signal holdout).
- **Accuracy**: the shipped hybrid RRF + utility bundle scored
  +4.87pp vs naive top-k embedding retrieval (p=0.0005) and was
  non-inferior to full dump (+1.12pp, p=0.42) on the lab's 178-signal
  holdout. Utility acts mostly as a **downweighting prior** (lab:
  61/79 memories had negative measured utility — the gain came from
  suppressing harmful exemplars, not finding golden ones).
- **Crossover**: below a few dozen memories, full dump is simpler and
  competitive. Above ~100 memories, retrieval dominates on cost while
  holding accuracy. Re-measure the crossover on your own corpus.

Excluded from the package because they did not earn their keep in the
lab ablation: MMR diversity, temporal weighting, Clef write-time
enrichment. Do not re-add them without an ablation on your data.

---

## 7. Deployment checklist

1. Choose embedding model and pin its version; record the dimension.
2. Run the pgvector migration (§3) against the memory-bank database.
3. Implement `TranscriptSink` for the trace store; verify the scrub gate
   runs before every write (fixture: a leaking record must raise, not
   write).
4. Implement `rehydrate`'s `query_fn` against the trace store; verify a
   memory round-trips: attach provenance → rehydrate → excerpts match.
5. Load utility values (`HybridBank.load_utility`, dict or JSON path);
   missing entries contribute 0.0.
6. Set SLO budgets (§5) in config; wire alerts.
7. Size the result cache from a week of measured query repetition (§4).
8. Re-run the package test suite (`python3 -m signal_action.tests.*`)
   in the deployment environment as a smoke check.
