"""Platform adapters: NormalizedRecord + one adapter per transcript source.

Status: fixture-tested (lab: 8/8 end-to-end, 10/10 reasoning-stream;
no live verification).

Shipped:
  base        NormalizedRecord dataclass + BaseAdapter interface
  openclaw    OpenClaw session JSONL (also covers Grokbot's fork via
              tag_platform="grokbot")
  claude_code Claude Code ~/.claude/projects JSONL
  muse_db     muse.db runtime.events rows -> normalize_rows()

Blocked (excluded from this distill): Instinct — a hosted iMessage agent
with no documented programmatic transcript export as of 2026-10-05.
No adapter ships; see README.md. Calling for it here would silently
degrade the pipeline, so it is a loud absence instead.
"""
from signal_action.capture.adapters.base import BaseAdapter, NormalizedRecord
from signal_action.capture.adapters.openclaw import OpenClawAdapter
from signal_action.capture.adapters.claude_code import ClaudeCodeAdapter
from signal_action.capture.adapters.muse_db import MuseAdapter

__all__ = ["BaseAdapter", "NormalizedRecord", "OpenClawAdapter", "ClaudeCodeAdapter", "MuseAdapter"]
