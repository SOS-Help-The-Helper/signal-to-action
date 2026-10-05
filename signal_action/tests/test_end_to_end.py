"""End-to-end + scrubber tests. Synthetic data only — no real PII anywhere.

Run from the distill root: python3 -m signal_action.tests.test_end_to_end

NOTE on key-shaped secrets (see tests/README.md): the file-write
pipeline redacts key literals (sk-..., ghp_..., AKIA...) on sight — which
is the correct safety behavior. So fixtures carry <redacted> placeholders
where a key context is needed, and key-shaped secrets are built at RUNTIME
here (the _mk helper), exactly as the lab tests do. Coverage is not lost:
every key shape the scrubber handles is probed with a real, correctly
shaped value.
"""
import json
import os

from signal_action.capture.adapters.base import NormalizedRecord
from signal_action.capture.adapters.openclaw import parse_jsonl as parse_oc
from signal_action.capture.adapters.claude_code import parse_jsonl as parse_cc
from signal_action.capture.adapters.muse_db import normalize_rows as muse_normalize
from signal_action.capture.scrubber import ScrubResult, scrub, assert_clean
from signal_action.capture import feed as feed_mod
from signal_action.capture.feed import feed_records, prepare_record
from signal_action.capture.sinks import JsonlSink
from signal_action.provenance.provenance import (
    attach_provenance,
    rehydrate,
    verify_memory_against_source,
)

FIX = os.path.join(os.path.dirname(__file__), "fixtures")

# Key-shaped secrets are built at runtime (the file-write pipeline redacts
# key literals on sight — which is the correct safety behavior). Each is
# probed inside a realistic sentence, the way it appears in transcripts.
def _mk(prefix: str, body: str) -> str:
    return prefix + body

RUNTIME_SECRETS = {
    "openai_key": (_mk("sk-", "TestKeyAbc123Def456Ghi789jkl"),
                   "deploy with key sk-{body} tonight"),
    "github_pat": (_mk("ghp_", "TestAbc1234567890xyz"),
                   "token ghp-{body} expired"),
    "aws_key": (_mk("AKIA", "TEST1234567890AB"),
                "aws key AKIA{body} in us-east-1"),
    "xai_key": (_mk("xai-", "TestKey1234567890"),
                "xai key xai-{body} for grok"),
    "stripe_key": (_mk("sk_live_", "TestAbc1234567890"),
                   "stripe sk_live_{body} charged"),
    "bearer": ("Bearer " + _mk("", "AbcDefGhIjKlMnOp1234567890"),
               "auth Bearer {body} here"),
    "jwt": (_mk("eyJhbGciOi", "JIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJVadQssw0c"),
            "jwt eyJhbGciOi{rest}"),
}

# PII-shaped secrets (writable as literals — no key prefixes).
PLANTED = [
    "jane.doe@example.com",
    "+1-555-014-8890",
    "hunter2x9Q",                      # via "password is hunter2x9Q!"
    "123-45-6789",
    "4111 1111 1111 1111",
    "me:sup3rsecret@example.com",      # login shape
    "742 Evergreen Terrace",
]


def test_openclaw_parse():
    recs = parse_oc(os.path.join(FIX, "synth-openclaw.jsonl"), platform="openclaw")
    # m1..m7 minus nothing (m5 toolResult kept, compaction skipped, thinking skipped)
    assert len(recs) == 7, f"expected 7, got {len(recs)}"
    roles = [r.role for r in recs]
    assert roles == ["user", "assistant", "user", "assistant", "tool", "user", "assistant"], roles
    # thinking block must NOT be captured
    assert not any("PRIVATE REASONING" in r.content for r in recs)
    # tool_use collapsed to marker, not raw input (which held the key)
    m4 = recs[3]
    assert "[tool:deploy]" in m4.content
    assert "sk-TESTKEY" not in m4.content
    print("openclaw parse: OK")


def test_claude_code_parse():
    path = os.path.join(FIX, "synth-claude.jsonl")
    recs = parse_cc(path)
    assert len(recs) == 2, f"expected 2, got {len(recs)}"
    assert recs[0].role == "user" and recs[1].role == "assistant"
    assert "PRIVATE" not in recs[1].content  # thinking skipped
    print("claude_code parse: OK")


def test_muse_normalize():
    rows = json.load(open(os.path.join(FIX, "synth-muse-rows.json")))
    recs = muse_normalize(rows)
    assert len(recs) == 2, f"expected 2, got {len(recs)}"
    assert recs[0].role == "user" and recs[1].role == "assistant"
    assert recs[0].session_id == "chat-1"
    assert recs[1].message_id == "evt-2"
    print("muse normalize: OK")


def test_scrub_recall():
    """Every planted secret must be caught IN CONTEXT. A single miss is a FAIL.

    Note: bare random strings (e.g. a password alone) are unidentifiable
    without context — the scrubber catches them via the assignment phrasing
    ("password is X", "key: Y"). So we scrub the full fixture texts, not
    the secrets standalone.
    """
    texts = [
        open(os.path.join(FIX, "synth-openclaw.jsonl")).read(),
        open(os.path.join(FIX, "synth-claude.jsonl")).read(),
        open(os.path.join(FIX, "synth-muse-rows.json")).read(),
    ]
    misses = []
    for text in texts:
        out = scrub(text).text
        for secret in PLANTED:
            if secret in out:
                misses.append(secret)
    # key-shaped secrets, probed in realistic sentence context
    for name, (secret, _template) in RUNTIME_SECRETS.items():
        probe = f"here is the credential {secret} for the deploy"
        if secret in scrub(probe).text:
            misses.append(f"{name}:{secret[:12]}...")
    # de-dupe, keep order
    seen = []
    for m in misses:
        if m not in seen:
            seen.append(m)
    assert not seen, f"SCRUBBER MISSED: {seen}"
    total = len(PLANTED) + len(RUNTIME_SECRETS)
    print(f"scrub recall: {total}/{total} planted secrets caught in context")


def test_scrub_markers_preserve_structure():
    r = scrub("call me at +1-555-014-8890 tomorrow")
    assert r.text == "call me at [REDACTED:phone] tomorrow", r.text
    assert r.redactions, "redactions list must be non-empty"
    print("scrub markers: OK")


def test_assert_clean():
    # Post-scrub fixture texts must pass the leak check.
    texts = [
        open(os.path.join(FIX, "synth-openclaw.jsonl")).read(),
        open(os.path.join(FIX, "synth-claude.jsonl")).read(),
        open(os.path.join(FIX, "synth-muse-rows.json")).read(),
    ]
    for text in texts:
        assert_clean(scrub(text).text)
    # Shape-based leaks are flaggable standalone (no context needed).
    standalone = ["jane.doe@example.com", "+1-555-014-8890"]
    standalone += [secret for secret, _ in RUNTIME_SECRETS.values()]
    for secret in standalone:
        try:
            assert_clean(f"x {secret} y")
        except ValueError:
            continue
        raise AssertionError("assert_clean failed to flag a shape-based secret")
    print("assert_clean: OK")


def test_provenance_roundtrip():
    store: dict = {}

    def fake_query(tids):
        return {t: store[t] for t in tids if t in store}

    # simulate feed: store scrubbed excerpts keyed by trace id
    recs = parse_oc(os.path.join(FIX, "synth-openclaw.jsonl"), platform="openclaw")
    trace_ids = []
    for i, rec in enumerate(recs):
        sr = scrub(rec.content)
        assert_clean(sr.text)
        tid = f"trace-synth-{i}"
        store[tid] = sr.text
        trace_ids.append(tid)

    memory = {"id": "mem-1", "text": "user prefers morning calls"}
    attach_provenance(memory, trace_ids[:3])
    assert memory["source_trace_ids"] == trace_ids[:3]
    # additive, no dupes
    attach_provenance(memory, trace_ids[:2])
    assert memory["source_trace_ids"] == trace_ids[:3]

    v = verify_memory_against_source(memory, query_fn=fake_query)
    assert v["rehydrated_count"] == 3, v
    assert v["missing"] == []
    # rehydrated excerpt matches what was fed (scrubbed verbatim)
    assert v["excerpts"][trace_ids[0]] == store[trace_ids[0]]

    # missing trace id is explicit, never silent
    v2 = verify_memory_against_source({"id": "m2", "source_trace_ids": ["nope"]},
                                      query_fn=fake_query)
    assert v2["missing"] == ["nope"] and v2["rehydrated_count"] == 0
    print("provenance roundtrip: OK")


def test_rehydrate_shape():
    """Distill change vs lab: rehydrate returns {"excerpts", "missing"}
    instead of stuffing a magic "_missing" key into the excerpts dict."""
    v = rehydrate(["a", "b"], query_fn=lambda tids: {"a": "excerpt-a"})
    assert v == {"excerpts": {"a": "excerpt-a"}, "missing": ["b"]}, v
    assert "_missing" not in v["excerpts"]
    print("rehydrate shape: OK")


def test_rehydrate_requires_query_fn():
    """No default that shells out: query_fn is required, and a missing one
    fails loudly at call time."""
    try:
        rehydrate(["a"], None)
    except ValueError:
        pass
    else:
        raise AssertionError("rehydrate without query_fn did not raise")
    print("rehydrate requires query_fn: OK")


def test_feed_dry_run():
    """Dry-run prepares (scrub + leak-check) without writing. The lab's
    baked-in INSERT SQL is gone; the equivalent invariant is: every
    prepared record is leak-free, correctly typed, and tagged."""
    recs = parse_oc(os.path.join(FIX, "synth-openclaw.jsonl"), platform="openclaw")
    out = feed_records(recs, dry_run=True)
    assert len(out) == 7
    for res in out:
        rec = res["record"]
        assert rec.trace_type == "agent-transcript", rec.trace_type
        assert rec.intent.startswith("transcript:"), rec.intent
        assert "transcript-capture" in rec.tags
        assert res["redactions"] == rec.redactions
        # scrubbed: no planted secret survives in any prepared record
        blob = json.dumps({"content": rec.content, "metadata": rec.metadata})
        for secret in PLANTED:
            assert secret not in blob, f"leak in prepared record: {secret}"
    print("feed dry_run: OK")


def test_feed_refuses_on_leak():
    """Safety invariant: if post-scrub text still matches a leak pattern,
    the feed raises and nothing is written. Simulated by disabling the
    scrub (white-box), so assert_clean sees raw fixture text."""
    real_scrub = feed_mod.scrub
    try:
        feed_mod.scrub = lambda text: ScrubResult(text=text or "", redactions=[])
        recs = parse_oc(os.path.join(FIX, "synth-openclaw.jsonl"), platform="openclaw")
        try:
            feed_records(recs, dry_run=True)
        except ValueError:
            pass  # expected: assert_clean caught the leak
        else:
            raise AssertionError("feed did not refuse a leaking record")
    finally:
        feed_mod.scrub = real_scrub
    print("feed leak refusal: OK")


def test_feed_write_requires_sink():
    """No production backend ships by design: non-dry-run without a sink
    fails loudly instead of guessing where to write."""
    recs = parse_oc(os.path.join(FIX, "synth-openclaw.jsonl"), platform="openclaw")
    try:
        feed_records(recs, dry_run=False)
    except ValueError:
        pass
    else:
        raise AssertionError("feed_records(write) without a sink did not raise")
    print("feed write requires sink: OK")


def test_feed_sink_write():
    """JsonlSink round trip: 7 records in, 7 scrubbed lines out."""
    import tempfile
    recs = parse_oc(os.path.join(FIX, "synth-openclaw.jsonl"), platform="openclaw")
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "out.jsonl")
        out = feed_records(recs, sink=JsonlSink(path), dry_run=False)
        assert len(out) == 7
        assert all(r["storage_id"] for r in out)
        lines = open(path, encoding="utf-8").read().splitlines()
        assert len(lines) == 7, f"expected 7 lines, got {len(lines)}"
        blob = "\n".join(lines)
        for secret in PLANTED:
            assert secret not in blob, f"leak in sink output: {secret}"
        assert "[REDACTED:" in blob
    print("feed sink write: OK")


if __name__ == "__main__":
    test_openclaw_parse()
    test_claude_code_parse()
    test_muse_normalize()
    test_scrub_recall()
    test_scrub_markers_preserve_structure()
    test_assert_clean()
    test_provenance_roundtrip()
    test_rehydrate_shape()
    test_rehydrate_requires_query_fn()
    test_feed_dry_run()
    test_feed_refuses_on_leak()
    test_feed_write_requires_sink()
    test_feed_sink_write()
    print("\nALL TESTS PASSED")
