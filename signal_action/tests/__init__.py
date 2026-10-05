"""Fixture-tested suite for signal_action.capture + signal_action.provenance
+ signal_action.retrieval + signal_action.loops.

Status: fixture-tested (synthetic data only — no real PII, no secrets,
no live capture, no DB touches).

Run from the distill root:
  python3 -m signal_action.tests.test_end_to_end
  python3 -m signal_action.tests.test_reasoning_stream
  python3 -m signal_action.tests.test_retrieval
  python3 -m signal_action.tests.test_loops
"""
