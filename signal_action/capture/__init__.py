"""Transcript capture: adapters -> scrub -> feed.

Status: fixture-tested (lab: 8/8 end-to-end, 10/10 reasoning-stream;
no live verification).

Public surface:
  NormalizedRecord, BaseAdapter           (adapters.base)
  OpenClawAdapter, ClaudeCodeAdapter, MuseAdapter
                                         (adapters.* — Grokbot rides the
                                          OpenClaw adapter with
                                          tag_platform="grokbot")
  scrub, assert_clean, ScrubResult        (scrubber)
  ScrubbedRecord, TranscriptSink, JsonlSink
                                         (sinks)
  prepare_record, feed_records, filter_stream, main
                                         (feed)

Blocked (no adapter ships): Instinct — hosted iMessage agent with no
documented transcript export as of 2026-10-05. See README.md.
"""
from signal_action.capture.adapters.base import BaseAdapter, NormalizedRecord
from signal_action.capture.adapters.openclaw import OpenClawAdapter, parse_jsonl as parse_openclaw_jsonl
from signal_action.capture.adapters.claude_code import ClaudeCodeAdapter, parse_jsonl as parse_claude_code_jsonl
from signal_action.capture.adapters.muse_db import MuseAdapter, normalize_rows as muse_normalize_rows
from signal_action.capture.scrubber import ScrubResult, assert_clean, scrub
from signal_action.capture.sinks import JsonlSink, ScrubbedRecord, TranscriptSink
from signal_action.capture.feed import feed_records, filter_stream, main, prepare_record

__all__ = [
    "BaseAdapter",
    "NormalizedRecord",
    "OpenClawAdapter",
    "ClaudeCodeAdapter",
    "MuseAdapter",
    "parse_openclaw_jsonl",
    "parse_claude_code_jsonl",
    "muse_normalize_rows",
    "ScrubResult",
    "assert_clean",
    "scrub",
    "ScrubbedRecord",
    "TranscriptSink",
    "JsonlSink",
    "prepare_record",
    "feed_records",
    "filter_stream",
    "main",
]
