"""LTSV parser."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import LogEntry
from .kv import extract_common_fields


@dataclass(frozen=True, slots=True)
class LtsvParser:
    """Parse Labeled Tab-Separated Values (LTSV)."""

    def parse(self, line_no: int, line: str) -> LogEntry | None:
        """Parse an LTSV line into a LogEntry."""
        if "\t" not in line:
            return None
        fields: dict[str, str] = {}
        for field in line.split("\t"):
            if ":" not in field:
                continue
            key, value = field.split(":", 1)
            if not key:
                continue
            fields[key] = value

        if not fields:
            return None

        ts, level, message = extract_common_fields(fields)
        msg = message or line.strip()
        return LogEntry(
            line_no=line_no,
            timestamp=ts,
            level=level,
            message=msg,
            raw=line,
            meta={"ltsv": fields},
        )
