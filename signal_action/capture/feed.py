"""Transcript feed pipeline — scrub, leak-check, then write via a sink.

Status: fixture-tested (lab: 8/8 end-to-end, 10/10 reasoning-stream;
no live verification).

Pipeline: NormalizedRecord -> ScrubbedRecord -> TranscriptSink.write().

Safety invariant (kept from the lab): every record is scrubbed
(scrubber.scrub) and leak-checked (scrubber.assert_clean) BEFORE any
sink call. A record that fails assert_clean is never written —
prepare_record raises instead of returning a ScrubbedRecord.

Distill change vs the lab: the lab's feed baked in a Supabase INSERT
(signal_traces schema: trace_type, signal_layer, ::jsonb casts, subprocess
write to one project). Persistence is now a configurable sink interface
(see sinks.TranscriptSink). The only bundled sink is sinks.JsonlSink
(local file); production backends are deployer-wired. There is no
default that shells out anywhere in this module.
"""
from __future__ import annotations

import argparse
import os
from typing import Any, Dict, List, Optional

from .adapters.base import NormalizedRecord
from .adapters.openclaw import OpenClawAdapter
from .adapters.claude_code import ClaudeCodeAdapter
from .scrubber import scrub, assert_clean
from .sinks import ScrubbedRecord, TranscriptSink, JsonlSink

MAX_TEXT = 8000


def prepare_record(rec: NormalizedRecord) -> ScrubbedRecord:
    """Scrub + leak-check a record, producing the sink-neutral payload.

    Raises ValueError on a scrubber leak — the record is NEVER handed to
    a sink in that case (see the safety invariant above).
    """
    sr = scrub(rec.content)
    assert_clean(sr.text)  # never write a leaking record
    text = sr.text[:MAX_TEXT]
    trace_type = "agent-reasoning" if rec.stream == "reasoning" else "agent-transcript"
    metadata = {
        "platform": rec.platform,
        "role": rec.role,
        "stream": rec.stream,
        "ts": rec.ts,
        "scrub_redactions": [f"{n}:{m}" for n, m in sr.redactions],
        **rec.metadata,
    }
    return ScrubbedRecord(
        platform=rec.platform,
        agent_id=rec.agent_id,
        session_id=rec.session_id,
        ts=rec.ts,
        role=rec.role,
        content=text,
        message_id=rec.message_id,
        metadata=metadata,
        stream=rec.stream,
        trace_type=trace_type,
        intent="transcript:" + rec.role,
        tags=["transcript-capture", rec.platform, rec.stream],
        redactions=sr.redactions,
    )


def feed_records(records: List[NormalizedRecord],
                 sink: Optional[TranscriptSink] = None,
                 dry_run: bool = True) -> List[Dict[str, Any]]:
    """Feed records through scrub + leak-check, then to a sink.

    dry_run=True (default): prepare only, write nothing. Returns per-record
    {"message_id", "record": ScrubbedRecord, "redactions"}.

    dry_run=False: requires a sink. Returns per-record
    {"message_id", "storage_id", "redactions"}. Raises ValueError when no
    sink is configured — this distribution ships no production backend by
    design; pass e.g. sinks.JsonlSink(path) or your own TranscriptSink.
    """
    prepared = [prepare_record(r) for r in records]  # scrub+leak-check first
    if dry_run:
        return [{"message_id": p.message_id, "record": p,
                 "redactions": p.redactions} for p in prepared]
    if sink is None:
        raise ValueError(
            "feed_records(write) requires a sink: pass a TranscriptSink "
            "(e.g. sinks.JsonlSink(path)). This distribution ships no "
            "production backend by design."
        )
    results = []
    for p in prepared:
        storage_id = sink.write(p)
        results.append({"message_id": p.message_id, "storage_id": storage_id,
                        "redactions": p.redactions})
    return results


def filter_stream(records: List[NormalizedRecord], stream: str) -> List[NormalizedRecord]:
    """Keep only records of the requested stream ('messages'|'reasoning'|'all')."""
    if stream == "all":
        return list(records)
    if stream not in ("messages", "reasoning"):
        raise ValueError(f"unknown stream {stream!r} (want messages|reasoning|all)")
    return [r for r in records if r.stream == stream]


def _collect(platform: str, source: str, capture_thinking: bool) -> List[NormalizedRecord]:
    """Capture records from one platform source (file or directory)."""
    if platform in ("openclaw", "grokbot"):
        adapter = OpenClawAdapter(tag_platform=platform,
                                  capture_thinking=capture_thinking)
    elif platform == "claude_code":
        adapter = ClaudeCodeAdapter(capture_thinking=capture_thinking)
    elif platform == "muse":
        raise ValueError("muse capture runs through the muse.db tool (no CLI path); "
                         "feed pre-normalized rows via feed_records() instead")
    else:
        raise ValueError(f"unknown platform {platform!r}")
    paths: List[str] = []
    if os.path.isdir(source):
        for root, _dirs, files in os.walk(source):
            for fn in sorted(files):
                if ".jsonl" in fn:
                    paths.append(os.path.join(root, fn))
    else:
        paths = [source]
    out: List[NormalizedRecord] = []
    for p in paths:
        out.extend(adapter.iter_records(p))
    return out


def main(argv: List[str] = None) -> int:
    """CLI: python3 -m signal_action.capture.feed --platform openclaw --source <path>
    [--stream messages|reasoning|all] [--capture-thinking] [--write --jsonl-out <path>]

    Default is a dry-run (prepares records, writes nothing). --write persists
    via sinks.JsonlSink to --jsonl-out (required with --write); deployers
    wire their own TranscriptSink for real backends (see sinks.py).
    --capture-thinking is the explicit opt-in for the reasoning stream
    (agents where the operator owns the stack only); --stream reasoning
    without it fails loudly instead of silently feeding nothing.
    """
    ap = argparse.ArgumentParser(description="Feed scrubbed transcripts to a sink")
    ap.add_argument("--platform", required=True,
                    choices=["openclaw", "grokbot", "claude_code"],
                    help="platform adapter to use")
    ap.add_argument("--source", required=True,
                    help="session JSONL file or directory of them")
    ap.add_argument("--stream", default="all",
                    choices=["messages", "reasoning", "all"],
                    help="which stream(s) to feed (default: all)")
    ap.add_argument("--capture-thinking", action="store_true",
                    help="OPT-IN: capture thinking blocks as the reasoning stream "
                         "(agents where the operator owns the stack only)")
    ap.add_argument("--write", action="store_true",
                    help="actually write (default: dry-run)")
    ap.add_argument("--jsonl-out", default=None,
                    help="sink target for --write: append prepared records as "
                         "JSONL here (required with --write)")
    args = ap.parse_args(argv)

    if args.stream == "reasoning" and not args.capture_thinking:
        ap.error("--stream reasoning requires --capture-thinking (explicit opt-in)")

    records = _collect(args.platform, args.source, args.capture_thinking)
    kept = filter_stream(records, args.stream)
    print(f"captured {len(records)} records, feeding {len(kept)} "
          f"(stream={args.stream})")
    if args.write:
        if not args.jsonl_out:
            ap.error("--write requires --jsonl-out <path> in this distribution; "
                     "wire your own TranscriptSink for other backends (see sinks.py)")
        results = feed_records(kept, sink=JsonlSink(args.jsonl_out), dry_run=False)
    else:
        results = feed_records(kept, dry_run=True)
    n_reasoning = sum(1 for r in kept if r.stream == "reasoning")
    print(f"done: {len(results)} records "
          f"({n_reasoning} reasoning, {len(results) - n_reasoning} messages), "
          f"{'WROTE' if args.write else 'dry-run'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
