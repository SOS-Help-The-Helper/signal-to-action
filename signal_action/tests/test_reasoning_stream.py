"""Reasoning-stream tests (opt-in thinking capture). Synthetic data only.

Run from the distill root: python3 -m signal_action.tests.test_reasoning_stream

Covers: opt-in capture in openclaw/grokbot/claude_code adapters, default-off
behavior, scrub recall on reasoning content (incl. a runtime-built API key
inside a thinking block), feed trace_type='agent-reasoning', stream filter,
provenance wiring, and the CLI opt-in guard.

NOTE on key-shaped secrets (see tests/README.md): key literals are built
at runtime via _mk, never written as literals in fixtures or source.
"""
import json
import os

from signal_action.capture.adapters.openclaw import parse_jsonl as parse_oc
from signal_action.capture.adapters.claude_code import parse_jsonl as parse_cc
from signal_action.capture.scrubber import scrub, assert_clean
from signal_action.capture.feed import (
    feed_records, filter_stream, prepare_record, main as feed_main,
)
from signal_action.provenance.provenance import (
    attach_provenance, verify_memory_against_source,
)

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
OC_FIX = os.path.join(FIX, "synth-openclaw-thinking.jsonl")
CC_FIX = os.path.join(FIX, "synth-claude-thinking.jsonl")

# PII planted inside thinking blocks (writable literals; key shapes are
# runtime-built below because the file-write pipeline redacts key literals).
REASONING_PLANTED = [
    "jane.doe@example.com",
    "+1-555-014-8890",
    "hunter2x9Q",                    # via "password is hunter2x9Q"
    "me:sup3rsecret@example.com",    # login shape
    "742 Evergreen Terrace",
    "bob@example.org",
    "123-45-6789",
    "4111 1111 1111 1111",
]


def _mk(prefix: str, body: str) -> str:
    return prefix + body


def test_default_off_openclaw():
    recs = parse_oc(OC_FIX, platform="openclaw")
    assert not any(r.role == "reasoning" for r in recs), "thinking leaked into default capture"
    assert not any(r.stream == "reasoning" for r in recs)
    # messages-only: t1 user, t2 text, t5 user (t3 thinking-only skipped, t4 skipped)
    assert len(recs) == 3, f"expected 3, got {len(recs)}"
    assert [r.role for r in recs] == ["user", "assistant", "user"]
    # thinking text must not appear anywhere in message content
    assert not any("jane.doe@example.com" in r.content for r in recs)
    print("default-off openclaw: OK")


def test_opt_in_openclaw():
    recs = parse_oc(OC_FIX, platform="openclaw", capture_thinking=True)
    reasoning = [r for r in recs if r.stream == "reasoning"]
    messages = [r for r in recs if r.stream == "messages"]
    # t2 thinking, t3 thinking-only, t4 top-level thinking row
    assert len(reasoning) == 3, f"expected 3 reasoning, got {len(reasoning)}"
    assert all(r.role == "reasoning" for r in reasoning)
    # same session linkage as the message records
    assert all(r.session_id == "sess-think-001" for r in reasoning)
    assert all(r.session_id == "sess-think-001" for r in messages)
    # parent linkage on content-block thinking
    parents = {r.metadata.get("parent_message_id") for r in reasoning}
    assert "t2" in parents and "t3" in parents, parents
    # message records unchanged by opt-in (thinking excluded from text)
    assert len(messages) == 3
    t2 = next(r for r in messages if r.message_id == "t2")
    assert t2.content == "Sure, drafting now."
    assert "jane.doe@example.com" not in t2.content
    # thinking-only message still yields its reasoning record
    t3r = next(r for r in reasoning if r.metadata.get("parent_message_id") == "t3")
    assert "sup3rsecret" in t3r.content
    print("opt-in openclaw: OK")


def test_opt_in_grokbot_platform_tag():
    recs = parse_oc(OC_FIX, platform="grokbot", capture_thinking=True)
    reasoning = [r for r in recs if r.stream == "reasoning"]
    assert reasoning and all(r.platform == "grokbot" for r in reasoning)
    print("grokbot platform tag: OK")


def test_claude_code():
    off = parse_cc(CC_FIX)
    assert len(off) == 2 and not any(r.stream == "reasoning" for r in off)
    on = parse_cc(CC_FIX, capture_thinking=True)
    reasoning = [r for r in on if r.stream == "reasoning"]
    assert len(reasoning) == 1, f"expected 1, got {len(reasoning)}"
    r = reasoning[0]
    assert r.role == "reasoning" and r.session_id == "cc-think-1"
    assert r.metadata.get("parent_message_id") == "a1"
    # message text excludes thinking
    a1 = next(x for x in on if x.message_id == "a1")
    assert a1.content == "Plan looks good."
    print("claude_code opt-in: OK")


def test_scrub_reasoning():
    recs = parse_oc(OC_FIX, platform="openclaw", capture_thinking=True)
    recs += parse_cc(CC_FIX, capture_thinking=True)
    reasoning = [r for r in recs if r.stream == "reasoning"]
    assert len(reasoning) == 4
    misses = []
    for r in reasoning:
        out = scrub(r.content).text
        assert_clean(out)  # post-scrub leak check must pass
        for secret in REASONING_PLANTED:
            if secret in out:
                misses.append(secret)
        assert "[REDACTED:" in out, f"no markers in scrubbed reasoning: {out[:60]}"
    assert not misses, f"SCRUBBER MISSED IN REASONING: {misses}"
    print(f"scrub reasoning: OK ({len(REASONING_PLANTED)}/{len(REASONING_PLANTED)} planted PII caught)")


def test_runtime_key_in_thinking():
    """An API key inside a thinking block must be caught like anywhere else."""
    key = _mk("sk-", "ThinkKeyAbc123Def456Ghi789jkl")
    row = {"type": "message", "id": "k1", "timestamp": "2026-10-05T19:20:00Z",
           "message": {"role": "assistant", "content": [
               {"type": "thinking",
                "thinking": f"Considering whether to use deploy key {key} for this."},
               {"type": "text", "text": "Working on it."}]}}
    path = "/tmp/synth-thinking-key.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "session", "sessionId": "sess-key-1"}) + "\n")
        fh.write(json.dumps(row) + "\n")
    recs = parse_oc(path, platform="openclaw", capture_thinking=True)
    reasoning = [r for r in recs if r.stream == "reasoning"]
    assert len(reasoning) == 1
    out = scrub(reasoning[0].content).text
    assert key not in out, "API KEY LEAKED FROM THINKING BLOCK"
    assert "[REDACTED:api_key]" in out
    assert_clean(out)
    os.remove(path)
    print("runtime key in thinking: OK")


def test_feed_reasoning_trace_type():
    """The lab's 'agent-reasoning' trace_type survives the distill as
    ScrubbedRecord.trace_type (no baked-in SQL anymore)."""
    recs = parse_oc(OC_FIX, platform="openclaw", capture_thinking=True)
    reasoning = [r for r in recs if r.stream == "reasoning"]
    out = feed_records(reasoning, dry_run=True)
    assert len(out) == 3
    for res in out:
        rec = res["record"]
        assert rec.trace_type == "agent-reasoning", rec.trace_type
        assert rec.intent == "transcript:reasoning", rec.intent
        assert "reasoning" in rec.tags, rec.tags
        assert "sess-think-001" in json.dumps({"s": rec.session_id})
        # zero planted secrets in any prepared record
        blob = json.dumps({"content": rec.content, "metadata": rec.metadata})
        for secret in REASONING_PLANTED:
            assert secret not in blob, f"leak in prepared record: {secret}"
    # messages still get the old trace type
    mrec = next(r for r in recs if r.stream == "messages")
    assert prepare_record(mrec).trace_type == "agent-transcript"
    print("feed trace_type: OK")


def test_filter_stream():
    recs = parse_oc(OC_FIX, platform="openclaw", capture_thinking=True)
    assert len(filter_stream(recs, "reasoning")) == 3
    assert len(filter_stream(recs, "messages")) == 3
    assert len(filter_stream(recs, "all")) == 6
    try:
        filter_stream(recs, "nope")
    except ValueError:
        pass
    else:
        raise AssertionError("filter_stream accepted a bad stream")
    print("filter_stream: OK")


def test_provenance_reasoning():
    store = {}
    recs = parse_oc(OC_FIX, platform="openclaw", capture_thinking=True)
    reasoning = [r for r in recs if r.stream == "reasoning"]
    tids = []
    for i, r in enumerate(reasoning):
        sr = scrub(r.content)
        assert_clean(sr.text)
        tid = f"trace-reason-{i}"
        store[tid] = sr.text
        tids.append(tid)
    memory = {"id": "mem-r1", "text": "agent deliberates before answering"}
    attach_provenance(memory, tids)
    v = verify_memory_against_source(
        memory, query_fn=lambda ts: {t: store[t] for t in ts if t in store})
    assert v["rehydrated_count"] == 3 and v["missing"] == []
    # mixed memory: message + reasoning traces together
    attach_provenance(memory, ["trace-msg-0"])
    assert set(memory["source_trace_ids"]) == set(tids + ["trace-msg-0"])
    print("provenance reasoning: OK")


def test_cli_opt_in_guard():
    # --stream reasoning WITHOUT --capture-thinking must fail loudly
    try:
        feed_main(["--platform", "openclaw", "--source", OC_FIX,
                   "--stream", "reasoning"])
    except SystemExit as e:
        assert e.code != 0, "expected non-zero exit"
    else:
        raise AssertionError("--stream reasoning without --capture-thinking did not fail")
    # with the opt-in flag, dry-run succeeds
    rc = feed_main(["--platform", "openclaw", "--source", OC_FIX,
                    "--stream", "reasoning", "--capture-thinking"])
    assert rc == 0
    print("cli opt-in guard: OK")


def test_cli_write_requires_sink_target():
    # --write without --jsonl-out must fail loudly (no backend by design)
    try:
        feed_main(["--platform", "openclaw", "--source", OC_FIX, "--write"])
    except SystemExit as e:
        assert e.code != 0, "expected non-zero exit"
    else:
        raise AssertionError("--write without --jsonl-out did not fail")


def test_cli_write_jsonl_out():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "feed.jsonl")
        rc = feed_main(["--platform", "openclaw", "--source", OC_FIX,
                        "--write", "--jsonl-out", out, "--capture-thinking"])
        assert rc == 0
        lines = open(out, encoding="utf-8").read().splitlines()
        assert len(lines) == 6, f"expected 6 lines, got {len(lines)}"
        blob = "\n".join(lines)
        for secret in REASONING_PLANTED:
            assert secret not in blob, f"leak in CLI sink output: {secret}"
    print("cli write --jsonl-out: OK")


if __name__ == "__main__":
    test_default_off_openclaw()
    test_opt_in_openclaw()
    test_opt_in_grokbot_platform_tag()
    test_claude_code()
    test_scrub_reasoning()
    test_runtime_key_in_thinking()
    test_feed_reasoning_trace_type()
    test_filter_stream()
    test_provenance_reasoning()
    test_cli_opt_in_guard()
    test_cli_write_requires_sink_target()
    test_cli_write_jsonl_out()
    print("\nALL REASONING-STREAM TESTS PASSED")
