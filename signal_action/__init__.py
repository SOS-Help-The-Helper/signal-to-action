"""Signal-to-Action framework — distilled public modules.

Status: fixture-tested (lab baseline: 8/8 end-to-end, 10/10 reasoning-stream;
test_bank_provenance skipped — it touched the production DB).

This package is a clean-room distill of the lab's capture + provenance
modules: universal transcript capture (platform adapters, PII/secret
scrubber, feed pipeline) and provenance pointers with verbatim
rehydration. Production backends (Supabase, CLIs, DB refs) are STRIPPED:
persistence and querying are injectable interfaces the deployer wires up.

Subpackages:
  signal_action.capture     — adapters, scrubber, feed pipeline, sinks
  signal_action.provenance  — attach_provenance / rehydrate /
                              verify_memory_against_source
  signal_action.retrieval   — hybrid BM25 + embedding RRF retrieval with
                              utility weighting (deployable, no DB)
  signal_action.loops       — the loops framework as a design spec
                              (stages, inner loops, lanes, validate_loop)
"""
