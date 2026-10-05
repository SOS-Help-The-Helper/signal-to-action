"""Muse adapter — reads verbatim transcript from muse.db `runtime.events`.

Status: fixture-tested (lab: 8/8 end-to-end, 10/10 reasoning-stream;
no live verification). Lab note: the field mapping below was checked
against the live muse.db schema reference on 2026-10-05; this distill
itself is exercised only with synthetic rows.

READ-ONLY by construction: this module never writes to muse.db. It exposes:
  - CAPTURE_SQL: the exact SELECT to run via the muse.db tool
    (an agent holding the tool runs it; there is no muse.db CLI).
  - normalize_rows(rows): pure function turning raw rows into
    NormalizedRecords. Fully testable with synthetic rows.

Capture scope: event_kind='message' AND event_name IN
('message.user','message.assistant'). message.internal rows are system
settlement records, not transcript prose — excluded by default.
delta.presentation rows are UI deltas, excluded.

Private reasoning: this adapter captures ONLY the readable message content
fields above and never attempts to reach withheld columns or filtered
rows. If a query fails on an unknown column, that column is withheld —
do not work around it.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterator, List

from .base import BaseAdapter, NormalizedRecord

# Only the built-in functions / cast spellings listed in the lab's schema
# reference are accepted by muse.db. This query uses none beyond plain
# column selects.
CAPTURE_SQL = """
SELECT
  event_seq,
  event_id,
  event_name,
  role,
  transcript_surface,
  created_at,
  payload_json,
  chat_context_json
FROM runtime.events
WHERE event_kind = 'message'
  AND event_name IN ('message.user', 'message.assistant')
  AND event_seq > {after_seq}
ORDER BY event_seq ASC
LIMIT {limit}
""".strip()

# Same, scoped to one chat (chat_id lives inside payload_json chat_context).
CAPTURE_SQL_BY_CHAT = """
SELECT
  event_seq,
  event_id,
  event_name,
  role,
  transcript_surface,
  created_at,
  payload_json,
  chat_context_json
FROM runtime.events
WHERE event_kind = 'message'
  AND event_name IN ('message.user', 'message.assistant')
  AND event_seq > {after_seq}
ORDER BY event_seq ASC
LIMIT {limit}
""".strip()
# NOTE: chat scoping is applied in normalize_rows (payload_json parsing),
# because muse.db's reviewed function set has no jsonb containment operator.
# Pass chat_id to normalize_rows to filter.


def _content_of(payload_json: Any) -> str:
    if not payload_json:
        return ""
    try:
        payload = json.loads(payload_json) if isinstance(payload_json, str) else payload_json
    except (json.JSONDecodeError, TypeError):
        return ""
    content = payload.get("content", "")
    if isinstance(content, list):
        # content blocks: join text blocks, note non-text blocks
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, dict):
                parts.append(f"[{block.get('type', 'block')}]")
        return "".join(parts)
    return content if isinstance(content, str) else ""


def _chat_id_of(payload_json: Any) -> str:
    if not payload_json:
        return ""
    try:
        payload = json.loads(payload_json) if isinstance(payload_json, str) else payload_json
    except (json.JSONDecodeError, TypeError):
        return ""
    ctx = payload.get("chat_context") or {}
    return ctx.get("chat_id", "") if isinstance(ctx, dict) else ""


def normalize_rows(rows: List[Dict[str, Any]], chat_id: str = "") -> List[NormalizedRecord]:
    """Turn raw muse.db rows into NormalizedRecords.

    rows: list of dicts with keys event_seq, event_id, event_name, role,
          transcript_surface, created_at, payload_json, chat_context_json.
    chat_id: optional filter — keep only rows from this chat.
    """
    out: List[NormalizedRecord] = []
    for r in rows:
        event_name = r.get("event_name", "")
        if event_name not in ("message.user", "message.assistant"):
            continue
        cid = _chat_id_of(r.get("payload_json"))
        if chat_id and cid != chat_id:
            continue
        role = r.get("role") or ("user" if event_name == "message.user" else "assistant")
        content = _content_of(r.get("payload_json"))
        if not content:
            continue  # nothing verbatim to capture
        out.append(
            NormalizedRecord(
                platform="muse",
                agent_id=str(r.get("agent_id") or ""),
                session_id=cid or str(r.get("transcript_surface") or ""),
                ts=str(r.get("created_at") or ""),
                role="user" if role == "user" else "assistant" if role == "assistant" else "system",
                content=content,
                message_id=str(r.get("event_id") or r.get("event_seq") or ""),
                metadata={
                    "event_seq": r.get("event_seq"),
                    "event_name": event_name,
                    "transcript_surface": r.get("transcript_surface"),
                    "chat_id": cid,
                },
            )
        )
    return out


class MuseAdapter(BaseAdapter):
    platform = "muse"

    def describe_source(self) -> str:
        return (
            "muse.db runtime.events (read-only SELECT via the muse.db tool). "
            "SQL template: adapters.muse_db.CAPTURE_SQL; rows -> normalize_rows(). "
            "There is no muse.db CLI; an agent holding the tool runs the query."
        )

    def iter_records(self, source: Any, **kwargs) -> Iterator[NormalizedRecord]:
        # source = list of raw row dicts (from the muse.db tool).
        yield from normalize_rows(list(source or []), chat_id=kwargs.get("chat_id", ""))
