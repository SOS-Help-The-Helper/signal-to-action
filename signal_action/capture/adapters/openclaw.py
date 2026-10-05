"""OpenClaw adapter — reads session JSONL transcripts from disk.

Status: fixture-tested (lab: 8/8 end-to-end, 10/10 reasoning-stream;
no live verification).

Source layout:
  $OPENCLAW_STATE_DIR/agents/<agentId>/sessions/<sessionId>.jsonl
  default state dir: ~/.openclaw   (legacy: ~/.clawdbot)

JSONL shape: one `type: "session"` header row (session id, ISO ts, cwd),
followed by `type: "message"` wrapper rows whose `message` holds
`user` / `assistant` (text, thinking, toolCall blocks) / `toolResult`.
Entry types compaction/custom/branch_summary are skipped (matching
OpenClaw's own transcript readers).

Thinking blocks: SKIPPED by default (messages-only capture). Pass
capture_thinking=True to emit them as role="reasoning" / stream="reasoning"
records — opt-in, for agents where the operator owns the stack only.

This adapter ALSO covers Grokbot's OpenClaw-fork layout:
  $OPENCLAW_STATE_DIR/agents/<agentId>/sessions/  (default ~/.grokbot/...)
  same <session-id>.jsonl shape. Pass platform="grokbot" to tag rows
  accordingly.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterator, List, Optional

from .base import BaseAdapter, NormalizedRecord

STATE_CANDIDATES = [
    os.environ.get("OPENCLAW_STATE_DIR", ""),
    os.path.expanduser("~/.openclaw"),
    os.path.expanduser("~/.clawdbot"),
    os.path.expanduser("~/.grokbot"),
]


def _split_message(message: Dict[str, Any]) -> tuple:
    """Split a message into (visible_text, thinking_texts).

    thinking blocks are the agent's private reasoning. They are returned
    separately so the caller can capture them as reasoning-stream records
    (opt-in) or drop them (default). They are NEVER folded into the
    message's visible text.
    """
    role = message.get("role", "")
    content = message.get("content", "")
    if isinstance(content, str):
        return content, []
    if isinstance(content, list):
        parts = []
        thinking = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                parts.append(block.get("text", ""))
            elif btype == "thinking":
                t = block.get("thinking", block.get("text", ""))
                if t:
                    thinking.append(t)
            elif btype in ("tool_use", "toolCall"):
                parts.append(f"[tool:{block.get('name', '?')}]")
            elif btype in ("tool_result", "toolResult"):
                parts.append("[tool-result]")
        return "".join(parts), thinking
    return "", []


def _text_of_message(message: Dict[str, Any]) -> str:
    text, _ = _split_message(message)
    return text


def _role_of(message: Dict[str, Any]) -> str:
    role = message.get("role", "")
    if role in ("user", "assistant", "system"):
        return role
    if role in ("toolResult", "tool_result"):
        return "tool"
    return "system"


def parse_jsonl(path: str, platform: str = "openclaw",
                agent_id: str = "", capture_thinking: bool = False) -> List[NormalizedRecord]:
    """Parse one OpenClaw-format session JSONL into NormalizedRecords.

    capture_thinking: when True (OPT-IN, default False), `thinking` blocks
    inside assistant messages — and top-level `type: "thinking"` rows — are
    emitted as separate NormalizedRecords with role="reasoning" and
    stream="reasoning", linked to the same session_id. Use only for
    agents where the operator owns the stack. Default False preserves the
    messages-only behavior.
    """
    records: List[NormalizedRecord] = []
    session_id = os.path.splitext(os.path.basename(path))[0]
    # strip archive suffixes: <sid>.jsonl.reset.<ts> / .deleted.<ts>
    for suffix in (".reset.", ".deleted."):
        if suffix in session_id:
            session_id = session_id.split(suffix)[0]
    if not agent_id:
        # .../agents/<agentId>/sessions/<file>
        parts = os.path.normpath(path).split(os.sep)
        if "agents" in parts:
            agent_id = parts[parts.index("agents") + 1]

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue  # malformed lines are recoverable diagnostics; skip
            rtype = row.get("type", "")
            if rtype == "session":
                session_id = row.get("sessionId", row.get("id", session_id))
                continue
            if rtype == "thinking":
                # Top-level thinking row (some OpenClaw versions emit these).
                # Opt-in only; never captured by default.
                if capture_thinking:
                    t = row.get("thinking", row.get("text", row.get("content", "")))
                    if t:
                        records.append(_reasoning_record(
                            platform, agent_id, session_id,
                            str(row.get("timestamp", row.get("ts", ""))),
                            str(t),
                            str(row.get("id", f"{session_id}:{lineno}:thinking")),
                            {"source_path": path, "line": lineno,
                             "row_type": "thinking"}))
                continue
            if rtype != "message":
                continue  # compaction / custom / branch_summary: skip
            message = row.get("message", row)
            text, thinking_texts = _split_message(message)
            row_id = str(row.get("id", f"{session_id}:{lineno}"))
            if capture_thinking:
                for idx, t in enumerate(thinking_texts):
                    records.append(_reasoning_record(
                        platform, agent_id, session_id,
                        str(row.get("timestamp", row.get("ts", ""))),
                        t, f"{row_id}:thinking:{idx}",
                        {"source_path": path, "line": lineno,
                         "model": message.get("model", ""),
                         "parent_message_id": row_id,
                         "block_index": idx}))
            if not text:
                continue
            records.append(
                NormalizedRecord(
                    platform=platform,
                    agent_id=agent_id,
                    session_id=session_id,
                    ts=str(row.get("timestamp", row.get("ts", ""))),
                    role=_role_of(message),
                    content=text,
                    message_id=row_id,
                    metadata={
                        "source_path": path,
                        "line": lineno,
                        "model": message.get("model", ""),
                    },
                )
            )
    return records


def _reasoning_record(platform: str, agent_id: str, session_id: str,
                      ts: str, content: str, message_id: str,
                      metadata: Dict[str, Any]) -> NormalizedRecord:
    """Build a reasoning-stream record (opt-in thinking capture)."""
    return NormalizedRecord(
        platform=platform,
        agent_id=agent_id,
        session_id=session_id,
        ts=ts,
        role="reasoning",
        content=content,
        message_id=message_id,
        metadata=metadata,
        stream="reasoning",
    )


def find_session_files(state_dir: str = "") -> List[str]:
    """Locate all session JSONL files under a state dir (incl. archives)."""
    roots = [state_dir] if state_dir else [c for c in STATE_CANDIDATES if c]
    found: List[str] = []
    for root in roots:
        agents = os.path.join(root, "agents")
        if not os.path.isdir(agents):
            continue
        for agent in sorted(os.listdir(agents)):
            sdir = os.path.join(agents, agent, "sessions")
            if not os.path.isdir(sdir):
                continue
            for fn in sorted(os.listdir(sdir)):
                if ".jsonl" in fn:
                    found.append(os.path.join(sdir, fn))
    return found


class OpenClawAdapter(BaseAdapter):
    platform = "openclaw"

    def __init__(self, state_dir: str = "", tag_platform: str = "openclaw",
                 capture_thinking: bool = False):
        self.state_dir = state_dir
        self.tag_platform = tag_platform
        # Opt-in reasoning capture. Default False: messages only.
        # Set True only for agents where the operator owns the stack.
        self.capture_thinking = capture_thinking

    def describe_source(self) -> str:
        return (
            "OpenClaw session JSONL: $OPENCLAW_STATE_DIR/agents/<agentId>/sessions/"
            "<sessionId>.jsonl (defaults ~/.openclaw, legacy ~/.clawdbot). "
            "Grokbot fork: same layout under ~/.grokbot (pass tag_platform='grokbot'). "
            "capture_thinking=True additionally emits thinking blocks as "
            "role='reasoning' records (opt-in, operator-owned agents only)."
        )

    def iter_records(self, source: Any = None, **kwargs) -> Iterator[NormalizedRecord]:
        files = [source] if source else find_session_files(self.state_dir)
        if isinstance(source, list):
            files = source
        capture = kwargs.get("capture_thinking", self.capture_thinking)
        for path in files:
            yield from parse_jsonl(path, platform=self.tag_platform,
                                   capture_thinking=capture)
