"""Claude Code adapter — reads ~/.claude/projects JSONL transcripts.

Status: fixture-tested (lab: 8/8 end-to-end, 10/10 reasoning-stream;
no live verification).

Layout: ~/.claude/projects/<project-slug>/<sessionId>.jsonl
Row shape: {"type": "user"|"assistant", "message": {"role":..., "content":...},
            "timestamp": ..., "sessionId": ..., "uuid": ...}
Assistant content blocks: text / tool_use / thinking.

Thinking blocks: SKIPPED by default (messages-only capture). Pass
capture_thinking=True to emit them as role="reasoning" / stream="reasoning"
records — opt-in, for agents where the operator owns the stack only.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterator, List, Tuple

from .base import BaseAdapter, NormalizedRecord


def _split_content(content: Any) -> Tuple[str, List[str]]:
    """Split content blocks into (visible_text, thinking_texts)."""
    if isinstance(content, str):
        return content, []
    if isinstance(content, list):
        parts = []
        thinking = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "thinking":
                t = block.get("thinking", block.get("text", ""))
                if t:
                    thinking.append(t)
            elif block.get("type") == "tool_use":
                parts.append(f"[tool:{block.get('name', '?')}]")
            # thinking blocks: returned separately, never folded into text
        return "".join(parts), thinking
    return "", []


def _text_of(content: Any) -> str:
    text, _ = _split_content(content)
    return text


def parse_jsonl(path: str, capture_thinking: bool = False) -> List[NormalizedRecord]:
    """Parse one Claude Code session JSONL.

    capture_thinking: when True (OPT-IN, default False), `thinking` blocks
    are emitted as separate NormalizedRecords with role="reasoning" and
    stream="reasoning", linked to the same session_id. Operator-owned
    agents only.
    """
    records: List[NormalizedRecord] = []
    session_id = os.path.splitext(os.path.basename(path))[0]
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rtype = row.get("type", "")
            if rtype not in ("user", "assistant"):
                continue
            message = row.get("message", {})
            row_sid = row.get("sessionId", session_id)
            row_id = str(row.get("uuid", f"{session_id}:{lineno}"))
            text, thinking_texts = _split_content(message.get("content", ""))
            if capture_thinking:
                for idx, t in enumerate(thinking_texts):
                    records.append(NormalizedRecord(
                        platform="claude_code",
                        agent_id="",
                        session_id=row_sid,
                        ts=str(row.get("timestamp", "")),
                        role="reasoning",
                        content=t,
                        message_id=f"{row_id}:thinking:{idx}",
                        metadata={"source_path": path, "line": lineno,
                                  "model": message.get("model", ""),
                                  "parent_message_id": row_id,
                                  "block_index": idx},
                        stream="reasoning",
                    ))
            if not text:
                continue
            records.append(
                NormalizedRecord(
                    platform="claude_code",
                    agent_id="",
                    session_id=row_sid,
                    ts=str(row.get("timestamp", "")),
                    role=rtype,
                    content=text,
                    message_id=row_id,
                    metadata={"source_path": path, "line": lineno,
                              "model": message.get("model", "")},
                )
            )
    return records


def find_session_files() -> List[str]:
    root = os.path.expanduser("~/.claude/projects")
    found: List[str] = []
    if not os.path.isdir(root):
        return found
    for proj in sorted(os.listdir(root)):
        pdir = os.path.join(root, proj)
        if not os.path.isdir(pdir):
            continue
        for fn in sorted(os.listdir(pdir)):
            if fn.endswith(".jsonl"):
                found.append(os.path.join(pdir, fn))
    return found


class ClaudeCodeAdapter(BaseAdapter):
    platform = "claude_code"

    def __init__(self, capture_thinking: bool = False):
        # Opt-in reasoning capture. Default False: messages only.
        self.capture_thinking = capture_thinking

    def describe_source(self) -> str:
        return ("Claude Code session JSONL: ~/.claude/projects/<project>/<sessionId>.jsonl "
                "(capture_thinking=True additionally emits thinking blocks as "
                "role='reasoning' records — opt-in, operator-owned agents only)")

    def iter_records(self, source: Any = None, **kwargs) -> Iterator[NormalizedRecord]:
        files = [source] if isinstance(source, str) else (source or find_session_files())
        capture = kwargs.get("capture_thinking", self.capture_thinking)
        for path in files:
            yield from parse_jsonl(path, capture_thinking=capture)
