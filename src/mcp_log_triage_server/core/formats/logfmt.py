"""Logfmt parser."""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from ..models import LogEntry
from .kv import extract_common_fields


@dataclass(frozen=True, slots=True)
class LogfmtParser:
    """Parse logfmt key=value lines."""

    def parse(self, line_no: int, line: str) -> LogEntry | None:
        """Parse a logfmt line into a LogEntry."""
        try:
            tokens = shlex.split(line, posix=True)
        except ValueError:
            return None

        fields: dict[str, str] = {}
        for token in tokens:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
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
            meta={"logfmt": fields},
        )
