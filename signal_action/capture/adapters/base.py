"""Universal transcript capture layer — normalized record + adapter interface.

Status: fixture-tested (lab: 8/8 end-to-end, 10/10 reasoning-stream;
no live verification).

Every platform adapter emits NormalizedRecord rows. Downstream stages
(scrubber -> feed -> provenance) only ever see this shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional


@dataclass
class NormalizedRecord:
    """One verbatim transcript message, platform-neutral."""

    platform: str          # 'muse' | 'openclaw' | 'grokbot' | 'claude_code' | ...
    agent_id: str          # platform-local agent identity (may be '' if unknown)
    session_id: str        # platform-local session/conversation id
    ts: str                # ISO-8601 timestamp (as carried by the source)
    role: str              # 'user' | 'assistant' | 'system' | 'tool' | 'reasoning'
    content: str           # verbatim text content (pre-scrub)
    message_id: str = ""   # platform-local message/event id (may be '')
    metadata: Dict[str, Any] = field(default_factory=dict)
    # metadata carries: source_path / event_seq / chat_id / model / cost /
    # any platform-native fields useful for audit. Never secrets.
    stream: str = "messages"  # 'messages' | 'reasoning'
    # stream discriminates the two capture streams:
    #   'messages'  — the verbatim conversation record (all agents, default)
    #   'reasoning' — the agent's private deliberation (opt-in ONLY, for
    #                 agents where the operator owns the stack; never from
    #                 hosted platforms that withhold it).


class BaseAdapter:
    """Interface every platform adapter implements."""

    platform: str = "base"

    def iter_records(self, source: Any, **kwargs) -> Iterator[NormalizedRecord]:
        """Yield NormalizedRecords from a platform-native source."""
        raise NotImplementedError

    def describe_source(self) -> str:
        """Human-readable description of where this adapter reads from."""
        raise NotImplementedError
