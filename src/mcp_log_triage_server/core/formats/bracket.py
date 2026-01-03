"""Bracketed timestamp parser."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from ..models import LogEntry, LogLevel


@dataclass(frozen=True, slots=True)
class BracketTimestampParser:
    """Parse '<timestamp> [LEVEL] <message>' lines."""

    timestamp_formats: Sequence[str] = ("%Y-%m-%d %H:%M:%S",)
    default_level: LogLevel = LogLevel.UNKNOWN

    _re = re.compile(r"^(?P<ts>.+?)\s+\[(?P<level>[A-Za-z]+)\]\s+(?P<msg>.*)$")

    def _parse_ts(self, ts_str: str) -> datetime | None:
        """Parse a timestamp string using the configured formats."""
        for fmt in self.timestamp_formats:
            try:
                return datetime.strptime(ts_str, fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
        return None

    def parse(self, line_no: int, line: str) -> LogEntry | None:
        """Parse a bracketed timestamp line into a LogEntry."""
        m = self._re.match(line)
        if not m:
            return None

        ts = self._parse_ts(m.group("ts").strip())
        level_raw = m.group("level").upper()
        try:
            level = LogLevel(level_raw)
        except ValueError:
            level = self.default_level

        msg = m.group("msg").strip()
        return LogEntry(line_no=line_no, timestamp=ts, level=level, message=msg, raw=line)
