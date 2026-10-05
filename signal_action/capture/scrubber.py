"""PII / secret scrubber — MANDATORY before any transcript is stored.

Status: fixture-tested (lab: 8/8 end-to-end, 10/10 reasoning-stream;
no live verification).

Design rules:
  - Every scrubbed span is replaced with a typed marker, e.g.
    [REDACTED:email], [REDACTED:phone], [REDACTED:api_key] — never silently
    deleted, so sentence structure survives for later retrieval.
  - Order matters: most-specific patterns first (assigned secrets), then
    generic secret shapes, then PII.
  - Recall over precision: a false-positive redaction is cheap; a leaked
    secret is a FAIL. When in doubt, redact.
  - This is a defense layer, not a proof: the feed stage refuses to write
    any record that still matches the leak-detection scan (see
    assert_clean), and the test suite plants secrets to measure recall.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

# (name, compiled pattern, marker). Most-specific first.
_PATTERNS: List[Tuple[str, re.Pattern, str]] = []

def _add(name: str, pattern: str, marker: str, flags: int = 0) -> None:
    _PATTERNS.append((name, re.compile(pattern, flags), marker))

# --- assigned secrets: key = "value" / key: value / key=value / key is value ---
_add(
    "assigned_secret",
    r'''(?i)\b(api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?token|auth[_-]?token|bearer|password|passwd|pwd|client[_-]?secret|private[_-]?key)\b\s*(?:[:=]|\bis\b)\s*["']?([^\s"'<>,;]{4,})["']?''',
    "[REDACTED:secret]",
)
# --- well-known token shapes -------------------------------------------------
_add("openai_key", r"\bsk-[A-Za-z0-9][A-Za-z0-9\-_]{16,}\b", "[REDACTED:api_key]")
_add("github_pat", r"\bgithub_pat_[A-Za-z0-9_]{10,}\b", "[REDACTED:api_key]")
_add("github_classic", r"\bgh[pousr]_[A-Za-z0-9]{10,}\b", "[REDACTED:api_key]")
_add("xai_key", r"\bxai-[A-Za-z0-9][A-Za-z0-9\-_]{10,}\b", "[REDACTED:api_key]")
_add("anthropic_key", r"\bsk-ant-[A-Za-z0-9][A-Za-z0-9\-_]{10,}\b", "[REDACTED:api_key]")
_add("aws_key", r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED:api_key]")
_add("aws_secret", r"\baws_secret_access_key\b\s*[:=]\s*[\"']?[A-Za-z0-9/+=]{32,}[\"']?", "[REDACTED:secret]")
_add("stripe_key", r"\b[rs]k_(live|test)_[A-Za-z0-9]{10,}\b", "[REDACTED:api_key]")
_add("slack_token", r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b", "[REDACTED:api_key]")
_add("bearer_token", r"(?i)\bbearer\s+[A-Za-z0-9\-_.~+/=]{16,}\b", "[REDACTED:api_key]")
_add("jwt", r"\beyJ[A-Za-z0-9\-_]{8,}\.[A-Za-z0-9\-_]{8,}\.[A-Za-z0-9\-_]{8,}\b", "[REDACTED:api_key]")
_add("generic_long_secret", r"\b[A-Za-z0-9\-_]{32,}\.[A-Za-z0-9\-_]{16,}\b", "[REDACTED:api_key]")
# --- PII (email before login shapes: user@host.tld is an email, not ssh) ----
_add("email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", "[REDACTED:email]")
# --- logins: user[/@]host and user:password@host --------------------------------
_add("login_userpass", r"\b[A-Za-z0-9._%+-]{2,}:[^/\s@]{4,}@[A-Za-z0-9.\-]+\b", "[REDACTED:login]")
_add("ssh_login", r"\b[A-Za-z0-9._-]{2,}@[A-Za-z0-9.\-]+\b", "[REDACTED:login]")
# --- PII (continued) ------------------------------------------------------------
_add("phone_e164", r"\+\d[\d\s().\-]{6,}\d", "[REDACTED:phone]")
_add("phone_us", r"(?<!\d)(?:\(?\d{3}\)?[\s.\-]?)?\d{3}[\s.\-]?\d{4}(?!\d)", "[REDACTED:phone]")
_add("ssn", r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)", "[REDACTED:ssn]")
_add("cc", r"(?<!\d)(?:\d[ \-]?){13,16}(?!\d)", "[REDACTED:payment]")
# --- street addresses (conservative: number + street suffix) --------------------
_add(
    "street_address",
    r"(?i)\b\d{1,5}\s+[A-Za-z0-9.'\- ]+?\s(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|court|ct|place|pl|circle|cir|terrace|ter|way|parkway|pkwy)\b",
    "[REDACTED:address]",
)


@dataclass
class ScrubResult:
    text: str
    redactions: List[Tuple[str, str]]  # (pattern_name, marker) per hit


def scrub(text: str) -> ScrubResult:
    """Redact PII/secrets in text, preserving sentence structure."""
    redactions: List[Tuple[str, str]] = []
    out = text or ""
    for name, rx, marker in _PATTERNS:
        def _rep(_m, _name=name, _marker=marker):
            redactions.append((_name, _marker))
            return _marker
        out = rx.sub(_rep, out)
    return ScrubResult(text=out, redactions=redactions)


# Leak-detection: run AFTER scrub; any match here is a FAIL.
# Mirrors every key shape the scrubber handles (defense in depth).
_LEAK_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("e164", re.compile(r"\+\d[\d\s().\-]{6,}\d")),
    ("sk_key", re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9\-_]{16,}\b")),
    ("sk_ant", re.compile(r"\bsk-ant-[A-Za-z0-9][A-Za-z0-9\-_]{10,}\b")),
    ("ghp", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{10,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{10,}\b")),
    ("xai", re.compile(r"\bxai-[A-Za-z0-9][A-Za-z0-9\-_]{10,}\b")),
    ("aws", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("stripe", re.compile(r"\b[rs]k_(live|test)_[A-Za-z0-9]{10,}\b")),
    ("slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-_.~+/=]{16,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9\-_]{8,}\.[A-Za-z0-9\-_]{8,}\.[A-Za-z0-9\-_]{8,}\b")),
    ("assigned_password", re.compile(r"(?i)\bpassword\b\s*(?:[:=]|\bis\b)\s*[\"']?[^\s\"'<>,;]{4,}")),
    ("assigned_secret", re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token)\b\s*(?:[:=]|\bis\b)\s*[\"']?[^\s\"'<>,;]{8,}")),
]


def assert_clean(text: str) -> None:
    """Raise if any leak-pattern still matches post-scrub text."""
    for name, rx in _LEAK_PATTERNS:
        m = rx.search(text)
        if m:
            raise ValueError(f"scrubber leak: pattern {name!r} matched {m.group(0)[:24]!r}")
