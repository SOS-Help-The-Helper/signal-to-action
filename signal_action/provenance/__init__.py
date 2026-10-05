"""Provenance pointers + verbatim rehydration (non-compaction principle).

Status: fixture-tested (lab: 8/8 end-to-end, 10/10 reasoning-stream;
no live verification).

Functions:
  attach_provenance(memory, trace_ids) -> memory with source_trace_ids set
  rehydrate(trace_ids, query_fn)      -> {"excerpts": {tid: excerpt},
                                          "missing": [tid]}
  verify_memory_against_source(memory, query_fn) -> verification report

Query wiring: query_fn is REQUIRED and injectable — there is deliberately
no default. The lab's default shelled out to a Supabase CLI bound to a
specific project; a public package must not ship credential-bearing
defaults. Deployers inject their own lookup.
"""
from signal_action.provenance.provenance import (
    attach_provenance,
    rehydrate,
    verify_memory_against_source,
)

__all__ = ["attach_provenance", "rehydrate", "verify_memory_against_source"]
