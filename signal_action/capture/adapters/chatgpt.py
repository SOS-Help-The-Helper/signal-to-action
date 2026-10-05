"""ChatGPT adapter — parses a ChatGPT `conversations.json` export.

Status: fixture-tested (no live verification against a real export).

Export path: ChatGPT web -> Settings -> Data controls -> Export data.
You receive a zip containing `conversations.json`: a list of conversations,
each with `title`, `create_time` (epoch seconds), `id`, and a `mapping` of
node_id -> node. Each node carries an optional `message` with
`author.role` in {"user", "assistant", "system", "tool"},
`content.parts` (list; string entries joined, non-string entries skipped),
`create_time`, and `id`. Root nodes have `"message": null` and are skipped.

Records are ordered by message create_time (falling back to mapping order),
not by tree traversal, so a partially-pruned export still yields a
chronological record stream.

Gemini (no separate parser): Google Takeout -> Gemini Apps activity gives a
per-conversation JSON whose turns carry the same user/model text shape. Map
each turn to {"role": "user"|"assistant", "text": ..., "ts": ...} ("model"
-> "assistant") and pass the list to `records_from_turns(..., platform=
"gemini")`. Turn-list shape is deliberately minimal so any export that can
produce (role, text, timestamp) triples works without a dedicated parser.
"""
from __future__ import annotations

import datetime
import json
from typing import Any, Dict, Iterator, List, Optional

from .base import BaseAdapter, NormalizedRecord

PLATFORM = "chatgpt"

_ROLE_MAP = {
    "user": "user",
    "assistant": "assistant",
    "model": "assistant",  # Gemini Takeout role name
    "system": "system",
    "tool": "tool",
}


def _iso(ts: Any) -> str:
    """Best-effort ISO-8601 for an epoch-seconds timestamp; '' if unusable."""
    try:
        return datetime.datetime.fromtimestamp(
            float(ts), tz=datetime.timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def _text_of_parts(parts: Any) -> str:
    if not isinstance(parts, list):
        return ""
    return "".join(p for p in parts if isinstance(p, str))


def _node_message(node: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(node, dict):
        return None
    msg = node.get("message")
    return msg if isinstance(msg, dict) else None


def parse_conversations(data: Any) -> List[NormalizedRecord]:
    """Parse an already-loaded conversations.json payload (a list)."""
    records: List[NormalizedRecord] = []
    if not isinstance(data, list):
        return records
    for conv_idx, conv in enumerate(data):
        if not isinstance(conv, dict):
            continue
        conv_id = str(conv.get("id") or conv.get("conversation_id")
                      or f"conv-{conv_idx}")
        title = str(conv.get("title") or "")
        mapping = conv.get("mapping")
        if not isinstance(mapping, dict):
            continue
        # Collect (order_key, message) then sort by create_time so pruned
        # exports still come out chronological.
        pending: List[tuple] = []
        for order, node_id in enumerate(mapping):
            msg = _node_message(mapping[node_id])
            if msg is None:
                continue
            author = msg.get("author") or {}
            role = _ROLE_MAP.get(str(author.get("role") or "").lower())
            if role is None:
                continue
            content = msg.get("content") or {}
            text = _text_of_parts(content.get("parts"))
            if not text:
                continue
            create_time = msg.get("create_time")
            pending.append((create_time if isinstance(create_time, (int, float))
                            else float("inf"), order, node_id, msg, role, text))
        pending.sort(key=lambda t: (t[0], t[1]))
        for _, _, node_id, msg, role, text in pending:
            records.append(NormalizedRecord(
                platform=PLATFORM,
                agent_id="",
                session_id=conv_id,
                ts=_iso(msg.get("create_time")),
                role=role,
                content=text,
                message_id=str(msg.get("id") or node_id),
                metadata={"conversation_title": title,
                          "export_node_id": str(node_id)},
            ))
    return records


def parse_file(path: str) -> List[NormalizedRecord]:
    """Parse a conversations.json file from a ChatGPT data export."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return parse_conversations(json.load(fh))


def records_from_turns(turns: List[Dict[str, Any]], platform: str,
                       session_id: str) -> List[NormalizedRecord]:
    """Build records from minimal (role, text, ts) turn dicts.

    The Gemini Takeout path: map each turn to
    {"role": "user"|"assistant", "text": ..., "ts": epoch-seconds or ISO
    string} ("model" -> "assistant") and call with platform="gemini".
    """
    records: List[NormalizedRecord] = []
    for idx, turn in enumerate(turns):
        if not isinstance(turn, dict):
            continue
        role = _ROLE_MAP.get(str(turn.get("role") or "").lower())
        text = turn.get("text") or turn.get("content") or ""
        if role is None or not isinstance(text, str) or not text:
            continue
        ts = turn.get("ts") or turn.get("create_time") or ""
        ts_s = _iso(ts) if not isinstance(ts, str) else ts
        records.append(NormalizedRecord(
            platform=platform,
            agent_id="",
            session_id=session_id,
            ts=ts_s,
            role=role,
            content=text,
            message_id=str(turn.get("id") or f"{session_id}:{idx}"),
            metadata={"turn_index": idx},
        ))
    return records


def from_gemini_takeout(data: Any) -> List[NormalizedRecord]:
    """Best-effort parse of a Google Takeout Gemini Apps export.

    UNVERIFIED: the Takeout schema is not pinned here. This accepts either a
    list of {"role", "text", "ts"} turn dicts (see records_from_turns) or a
    list of conversation dicts shaped like {"id"/"title", "turns": [...]};
    anything else yields no records rather than wrong records.
    """
    records: List[NormalizedRecord] = []
    if isinstance(data, dict) and isinstance(data.get("turns"), list):
        data = [data]
    if not isinstance(data, list):
        return records
    for conv_idx, conv in enumerate(data):
        if not isinstance(conv, dict):
            continue
        turns = conv.get("turns")
        if not isinstance(turns, list):
            # Maybe the list itself is the turn list (single conversation).
            if conv_idx == 0 and all(isinstance(t, dict)
                                     and "text" in t for t in data):
                turns = data
            else:
                continue
        sid = str(conv.get("id") or conv.get("title") or f"gemini-{conv_idx}")
        records.extend(records_from_turns(turns, "gemini", sid))
        if turns is data:
            break
    return records


class ChatGPTAdapter(BaseAdapter):
    platform = PLATFORM

    def describe_source(self) -> str:
        return ("ChatGPT data export: conversations.json "
                "(Settings -> Data controls -> Export data)")

    def iter_records(self, source: Any = None, **kwargs) -> Iterator[NormalizedRecord]:
        if isinstance(source, str):
            yield from parse_file(source)
        elif isinstance(source, list):
            yield from parse_conversations(source)
