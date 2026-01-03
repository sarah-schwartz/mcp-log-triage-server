"""Syslog parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..models import LogEntry, LogLevel


@dataclass(frozen=True, slots=True)
class SyslogParser:
    """Parse Syslog RFC5424/RFC3164-style lines using PRI for severity."""

    _rfc5424 = re.compile(
        r"^<(?P<pri>\d{1,3})>(?P<ver>\d)\s+"
        r"(?P<ts>\S+)\s+"
        r"(?P<host>\S+)\s+"
        r"(?P<app>\S+)\s+"
        r"(?P<proc>\S+)\s+"
        r"(?P<msgid>\S+)\s*"
        r"(?P<sd>\[[^\]]*\]|-)?\s*"
        r"(?P<msg>.*)$"
    )

    _rfc3164 = re.compile(
        r"^<(?P<pri>\d{1,3})>"
        r"(?P<ts>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
        r"(?P<host>\S+)\s+"
        r"(?P<tag>[^:]+):\s*"
        r"(?P<msg>.*)$"
    )

    @staticmethod
    def level_from_pri(pri: int) -> LogLevel:
        """Map syslog PRI to a normalized severity."""
        sev = pri % 8  # 0..7
        if sev <= 2:
            return LogLevel.CRITICAL
        if sev == 3:
            return LogLevel.ERROR
        if sev == 4:
            return LogLevel.WARNING
        if sev == 5:
            return LogLevel.INFO
        if sev >= 6:
            return LogLevel.DEBUG
        return LogLevel.UNKNOWN

    @staticmethod
    def _parse_rfc5424_ts(ts_str: str) -> datetime | None:
        """Parse RFC5424 timestamps into UTC datetimes."""
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts.tzinfo is not None:
                ts = ts.astimezone(UTC)
            return ts
        except ValueError:
            return None

    @staticmethod
    def _parse_rfc3164_ts(ts_str: str) -> datetime | None:
        """Parse RFC3164 timestamps into UTC datetimes."""
        try:
            naive = datetime.strptime(ts_str, "%b %d %H:%M:%S")
        except ValueError:
            return None

        now = datetime.now(UTC)
        ts = naive.replace(year=now.year, tzinfo=UTC)
        if ts > now + timedelta(days=1):
            ts = ts.replace(year=now.year - 1)
        return ts

    @staticmethod
    def _syslog_meta(*, pri: int, host: str, app: str) -> dict:
        """Build structured syslog metadata."""
        sev = pri % 8
        fac = pri // 8
        return {
            "syslog": {
                "pri": pri,
                "severity": sev,
                "facility": fac,
                "host": host,
                "app": app,
            }
        }

    def parse(self, line_no: int, line: str) -> LogEntry | None:
        """Parse a syslog line into a LogEntry."""
        m = self._rfc5424.match(line)
        if m:
            pri = int(m.group("pri"))
            host = m.group("host")
            app = m.group("app")
            level = self.level_from_pri(pri)
            ts = self._parse_rfc5424_ts(m.group("ts"))

            msg = (m.group("msg") or "").strip()
            message = f"{host} {app}: {msg}" if msg else f"{host} {app}"

            return LogEntry(
                line_no=line_no,
                timestamp=ts,
                level=level,
                message=message,
                raw=line,
                meta=self._syslog_meta(pri=pri, host=host, app=app),
            )

        m = self._rfc3164.match(line)
        if m:
            pri = int(m.group("pri"))
            host = m.group("host")
            app = m.group("tag").strip()
            level = self.level_from_pri(pri)
            ts = self._parse_rfc3164_ts(m.group("ts"))

            msg = (m.group("msg") or "").strip()
            message = f"{host} {app}: {msg}" if msg else f"{host} {app}"

            return LogEntry(
                line_no=line_no,
                timestamp=ts,
                level=level,
                message=message,
                raw=line,
                meta=self._syslog_meta(pri=pri, host=host, app=app),
            )

        return None
