"""Access log parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from ..models import LogEntry, LogLevel


@dataclass(frozen=True, slots=True)
class AccessLogParser:
    """Parse Apache/Nginx access logs (Common/Combined format)."""

    _re = re.compile(
        r"^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+"
        r'"(?P<req>[^"]+)"\s+'
        r"(?P<status>\d{3})\s+"
        r"(?P<size>\S+)"
        r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)")?'
        r".*$"
    )

    @staticmethod
    def level_from_status(status: int) -> LogLevel:
        """Map HTTP status codes to normalized severity."""
        if 500 <= status <= 599:
            return LogLevel.ERROR
        if 400 <= status <= 499:
            return LogLevel.WARNING
        return LogLevel.INFO

    @staticmethod
    def _parse_ts(ts_str: str) -> datetime | None:
        """Parse access-log timestamps into UTC."""
        try:
            return datetime.strptime(ts_str, "%d/%b/%Y:%H:%M:%S %z").astimezone(UTC)
        except ValueError:
            return None

    def parse(self, line_no: int, line: str) -> LogEntry | None:
        """Parse an access-log line into a LogEntry."""
        m = self._re.match(line)
        if not m:
            return None

        ip = m.group("ip")
        req = m.group("req")
        status = int(m.group("status"))
        size_raw = m.group("size")

        level = self.level_from_status(status)
        ts = self._parse_ts(m.group("ts"))

        size = None
        if size_raw != "-":
            try:
                size = int(size_raw)
            except ValueError:
                size = None

        msg = f'{ip} "{req}" -> {status}'
        if size is not None:
            msg += f" ({size} bytes)"

        return LogEntry(line_no=line_no, timestamp=ts, level=level, message=msg, raw=line)
