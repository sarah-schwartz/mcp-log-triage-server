"""Redaction helpers for AI review."""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_RE = re.compile(r"\b(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}\b")
_JWT_RE = re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b")
_LONG_TOKEN_RE = re.compile(r"\b[a-zA-Z0-9_\-]{32,}\b")


def redact_text(text: str) -> str:
    """Redact sensitive tokens from log text."""
    text = _JWT_RE.sub("<REDACTED_JWT>", text)
    text = _EMAIL_RE.sub("<REDACTED_EMAIL>", text)
    text = _IPV4_RE.sub("<REDACTED_IP>", text)
    text = _IPV6_RE.sub("<REDACTED_IP>", text)
    text = _LONG_TOKEN_RE.sub("<REDACTED_TOKEN>", text)
    return text
