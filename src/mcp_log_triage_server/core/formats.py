"""Log parsing formats and scan configuration.

Contains parsers for common log formats (JSON lines, syslog, access logs, etc.).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from .models import LogEntry, LogLevel


class LogParser(Protocol):
    """Parser interface: return LogEntry if line matches, else None."""

    def parse(self, line_no: int, line: str) -> LogEntry | None:
        """Parse a log line into a LogEntry if recognized."""
        ...


@dataclass(frozen=True)
class ScanConfig:
    """Fast prefilter config for raw-bytes scanning."""

    tokens: dict[LogLevel, Sequence[bytes]]
    case_insensitive: bool = True


def default_scan_config() -> ScanConfig:
    """Default scan tokens for common log styles."""
    return ScanConfig(
        tokens={
            LogLevel.CRITICAL: (
                b"[CRITICAL]",
                b" CRITICAL ",
                b"[FATAL]",
                b" FATAL ",
                b" SEVERE ",
                b" PANIC ",
                b" EMERG ",
            ),
            LogLevel.ERROR: (
                b"[ERROR]",
                b" ERROR ",
                b' "level":"error"',
                b" level=error",
                b" EXCEPTION",
                b" TRACEBACK",
                b" FAILED",
                b" FAILURE",
            ),
            LogLevel.WARNING: (
                b"[WARNING]",
                b" WARNING ",
                b" WARN ",
                b' "level":"warning"',
                b" level=warning",
                b" DEPRECATED",
                b" RETRY",
                b" TIMEOUT",
            ),
            LogLevel.INFO: (
                b"[INFO]",
                b" INFO ",
                b' "level":"info"',
                b" level=info",
            ),
            LogLevel.DEBUG: (
                b"[DEBUG]",
                b" DEBUG ",
                b' "level":"debug"',
                b" level=debug",
                b" TRACE ",
            ),
        },
        case_insensitive=True,
    )


@dataclass(frozen=True, slots=True)
class CompositeParser:
    """Try parsers in order and return the first successful parse."""

    parsers: Sequence[LogParser]

    def parse(self, line_no: int, line: str) -> LogEntry | None:
        """Return the first successful parse from the configured parsers."""
        for p in self.parsers:
            out = p.parse(line_no, line)
            if out is not None:
                return out
        return None


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
