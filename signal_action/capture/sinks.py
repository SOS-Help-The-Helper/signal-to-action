"""Sink interface for the transcript feed — backend-neutral persistence.

Status: fixture-tested (lab: 8/8 end-to-end, 10/10 reasoning-stream;
no live verification).

The lab's feed baked in one backend (a Supabase INSERT against the
signal_traces schema with trace_type, signal_layer, and ::jsonb casts).
This distill replaces that with a configurable interface:

  class TranscriptSink — implement write(ScrubbedRecord) -> str
                        (returns the storage/trace id)

The only bundled sink is JsonlSink (local file, integration/testing).
Production backends (Supabase, Postgres, HTTP, ...) are wired by the
deployer — subclass TranscriptSink and pass it to feed_records() or
feed.main(..., --write --jsonl-out ...).
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class ScrubbedRecord:
    """Sink-neutral, scrubbed, leak-checked transcript record.

    Produced by feed.prepare_record() AFTER scrub + assert_clean pass.
    Sinks receive this shape — never raw transcript text.
    """

    platform: str
    agent_id: str
    session_id: str
    ts: str
    role: str
    content: str          # scrubbed verbatim (truncated to feed.MAX_TEXT)
    message_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    stream: str = "messages"  # 'messages' | 'reasoning'
    trace_type: str = "agent-transcript"  # 'agent-transcript' | 'agent-reasoning'
    intent: str = ""      # f'transcript:{role}'
    tags: List[str] = field(default_factory=list)
    redactions: List[Tuple[str, str]] = field(default_factory=list)


class TranscriptSink(ABC):
    """Persistence target for the transcript feed. Deployer-implemented."""

    @abstractmethod
    def write(self, record: ScrubbedRecord) -> str:
        """Persist one scrubbed record; return its storage id."""
        raise NotImplementedError


class JsonlSink(TranscriptSink):
    """Append prepared records as JSONL to a local file.

    Integration/testing default: `python3 -m signal_action.capture.feed
    --platform openclaw --source <path> --write --jsonl-out out.jsonl`.
    Creates parent directories as needed.
    """

    def __init__(self, path: str):
        self.path = path

    def write(self, record: ScrubbedRecord) -> str:
        parent = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(parent, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        return record.message_id or f"{record.session_id}:{record.ts}"
