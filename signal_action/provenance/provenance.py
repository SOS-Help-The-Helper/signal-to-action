"""Provenance pointers + verbatim rehydration (non-compaction principle).

Status: fixture-tested (lab: 8/8 end-to-end, 10/10 reasoning-stream;
no live verification). Pure functions — no DB, no subprocess, no network,
no credentials anywhere in this module.

Design: a memory (rule/exemplar) never replaces its source. Each memory
carries the trace IDs of the transcript records it was derived from
(`source_trace_ids`). When verification needs the original, `rehydrate`
pulls the verbatim excerpt back from the trace store by trace id — the
full scrubbed transcript text, not a summary. Typed traces with bounded
excerpts rehydrated on demand; the ledger is the verbatim source of truth.

Functions:
  attach_provenance(memory, trace_ids) -> memory with source_trace_ids set
      Additive and deduped; never overwrites existing provenance.
  rehydrate(trace_ids, query_fn) -> {"excerpts": {trace_id: excerpt},
                                     "missing": [trace_id]}
      query_fn: REQUIRED injectable callable taking a list of trace ids and
      returning {trace_id: excerpt}. There is deliberately NO default that
      shells out — the lab's default ran a Supabase CLI bound to a specific
      project, which a public package must not ship. Deployers inject their
      own lookup (a DB query, an HTTP call, a dict in tests).
  verify_memory_against_source(memory, query_fn) -> {memory_id, trace_ids,
      rehydrated_count, missing, excerpts}
      The verification primitive: a memory whose sources can't be
      rehydrated is unverifiable, and the caller decides what that means.

STRIPPED from the lab version (do not re-add here): attach_to_bank_memory,
rehydrate_for_memory, _bank_sql — they hardcoded a production database
reference (a project ref mislabeled "TEST" in a stale comment). Bank-level
wiring belongs in deployer code with explicit credentials, not in a
public package.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Sequence


def attach_provenance(memory: Dict[str, Any], trace_ids: Sequence[str]) -> Dict[str, Any]:
    """Attach source trace IDs to a memory dict.

    The memory keeps its own fields; source_trace_ids is additive and
    never overwrites existing provenance (dupes are skipped).
    """
    existing = list(memory.get("source_trace_ids") or [])
    for tid in trace_ids:
        if tid and tid not in existing:
            existing.append(tid)
    memory["source_trace_ids"] = existing
    return memory


def rehydrate(trace_ids: Sequence[str],
              query_fn: Callable[[Sequence[str]], Dict[str, str]]) -> Dict[str, Any]:
    """Pull verbatim excerpts for trace IDs. Missing IDs are reported, not hidden.

    Returns {"excerpts": {trace_id: excerpt}, "missing": [trace_id]}.
    query_fn is REQUIRED — see module docstring. Raises ValueError when
    it is not provided.
    """
    if query_fn is None:
        raise ValueError(
            "rehydrate requires an injected query_fn (callable taking a list "
            "of trace ids, returning {trace_id: excerpt}). This distribution "
            "ships no default — wire your own trace store lookup."
        )
    found = query_fn(list(trace_ids))
    missing = [t for t in trace_ids if t not in found]
    return {"excerpts": dict(found), "missing": missing}


def verify_memory_against_source(memory: Dict[str, Any],
                                 query_fn: Callable[[Sequence[str]], Dict[str, str]]
                                 ) -> Dict[str, Any]:
    """Rehydrate a memory's sources and report what came back.

    Returns {memory_id, trace_ids, rehydrated_count, missing, excerpts}.
    This is the verification primitive: a memory whose sources can't be
    rehydrated is unverifiable, and the caller decides what that means.
    """
    tids = list(memory.get("source_trace_ids") or [])
    result = rehydrate(tids, query_fn=query_fn)
    return {
        "memory_id": memory.get("id", memory.get("memory_id", "")),
        "trace_ids": tids,
        "rehydrated_count": len(result["excerpts"]),
        "missing": result["missing"],
        "excerpts": result["excerpts"],
    }
