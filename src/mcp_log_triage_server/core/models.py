"""Core data models for log triage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class LogLevel(str, Enum):
    """Normalized severity levels used by the triage pipeline."""

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class LogHit:
    """Fast-scan candidate (line number + inferred level + raw bytes)."""

    line_no: int
    level: LogLevel
    raw_line: bytes


@dataclass(frozen=True, slots=True)
class LogEntry:
    """Normalized log record produced by parsers and filters."""

    line_no: int
    timestamp: datetime | None  # can be None when timestamp is missing/unknown
    level: LogLevel
    message: str
    raw: str | None = None  # original decoded line (useful for debug/LLM)
    meta: dict[str, Any] | None = None  # structured extras (syslog pri/severity, etc.)
