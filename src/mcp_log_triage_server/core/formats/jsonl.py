"""JSON-lines parser."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from ..models import LogEntry, LogLevel


@dataclass(frozen=True, slots=True)
class JsonLinesParser:
    """Parse JSON-lines logs (one JSON object per line)."""

    time_keys: Sequence[str] = ("timestamp", "time", "ts")
    level_keys: Sequence[str] = ("level", "severity", "lvl", "log_level")
    msg_keys: Sequence[str] = ("message", "msg", "error", "detail")

    def parse(self, line_no: int, line: str) -> LogEntry | None:
        """Parse a JSON object line into a LogEntry."""
        s = line.strip()
        if not s or not (s.startswith("{") and s.endswith("}")):
            return None

        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            return None

        ts: datetime | None = None
        ts_val = None
        for k in self.time_keys:
            if k in obj:
                ts_val = obj[k]
                break
        if isinstance(ts_val, str):
            try:
                ts = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                if ts.tzinfo is not None:
                    ts = ts.astimezone(UTC)
            except ValueError:
                ts = None

        level = LogLevel.UNKNOWN
        lvl_val = None
        for k in self.level_keys:
            if k in obj:
                lvl_val = obj[k]
                break
        if isinstance(lvl_val, str):
            try:
                level = LogLevel(lvl_val.upper())
            except ValueError:
                level = LogLevel.UNKNOWN

        msg_val = None
        for k in self.msg_keys:
            if k in obj:
                msg_val = obj[k]
                break
        msg = str(msg_val) if msg_val is not None else s

        return LogEntry(line_no=line_no, timestamp=ts, level=level, message=msg, raw=line)
