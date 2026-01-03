"""Fallback parser based on severity keywords."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..models import LogEntry, LogLevel


@dataclass(frozen=True, slots=True)
class LooseLevelParser:
    """Fallback parser that detects level keywords anywhere in the line."""

    keywords: dict[LogLevel, Iterable[str]] | None = None

    def parse(self, line_no: int, line: str) -> LogEntry | None:
        """Parse a line by scanning for severity keywords."""
        kw = self.keywords or {
            LogLevel.CRITICAL: ("CRITICAL", "FATAL", "PANIC"),
            LogLevel.ERROR: ("ERROR", "EXCEPTION", "TRACEBACK", "FAILED"),
            LogLevel.WARNING: ("WARNING", "WARN", "TIMEOUT", "RETRY"),
            LogLevel.INFO: ("INFO",),
            LogLevel.DEBUG: ("DEBUG", "TRACE"),
        }
        upper = line.upper()
        for lvl, keys in kw.items():
            if any(k in upper for k in keys):
                return LogEntry(
                    line_no=line_no,
                    timestamp=None,
                    level=lvl,
                    message=line.strip(),
                    raw=line,
                )
        return None
