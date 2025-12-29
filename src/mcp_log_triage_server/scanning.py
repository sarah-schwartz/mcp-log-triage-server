from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Iterator, Optional, Sequence

from mcp_log_triage_server.formats import AccessLogParser, ScanConfig, SyslogParser, default_scan_config
from mcp_log_triage_server.models import LogHit, LogLevel


class DetectedFormat(str, Enum):
    """Best-effort classification of the log file format."""
    SYSLOG = "syslog"
    ACCESS = "access"
    JSONL = "jsonl"
    BRACKET = "bracket"
    UNKNOWN = "unknown"


_SEVERITY_PRIORITY: tuple[LogLevel, ...] = (
    LogLevel.CRITICAL,
    LogLevel.ERROR,
    LogLevel.WARNING,
    LogLevel.INFO,
    LogLevel.DEBUG,
    LogLevel.UNKNOWN,
)

# Fast recognizers (bytes)
_SYSLOG_PRI_RE = re.compile(rb"^<(?P<pri>\d{1,3})>")
_ACCESS_RE = re.compile(
    rb'^\S+\s+\S+\s+\S+\s+\[[^\]]+\]\s+"[^"]+"\s+(?P<status>\d{3})\s+'
)
_BRACKET_HINT_RE = re.compile(rb"\[\s*(ERROR|WARN(?:ING)?|INFO|DEBUG|CRITICAL)\s*\]", re.IGNORECASE)


def sniff_format(
    log_path: str | Path,
    *,
    sample_lines: int = 120,
    max_bytes_per_line: int = 4096,
) -> DetectedFormat:
    """Sample the first N lines and guess the log format."""
    path = Path(log_path)
    if not path.is_file():
        raise FileNotFoundError(f"Log file not found: {path}")

    syslog_hits = 0
    access_hits = 0
    json_hits = 0
    bracket_hits = 0
    seen = 0

    with path.open("rb") as f:
        for raw in f:
            seen += 1
            line = raw[:max_bytes_per_line].strip()
            if not line:
                if seen >= sample_lines:
                    break
                continue

            if _ACCESS_RE.match(line):
                access_hits += 1
            if _SYSLOG_PRI_RE.match(line):
                syslog_hits += 1
            if line.startswith(b"{") and line.endswith(b"}"):
                json_hits += 1
            if _BRACKET_HINT_RE.search(line):
                bracket_hits += 1

            if seen >= sample_lines:
                break

    threshold = max(3, sample_lines // 10)

    # Prefer strongest signals (ACCESS/SYSLOG usually have distinctive shapes)
    if access_hits >= threshold:
        return DetectedFormat.ACCESS
    if syslog_hits >= threshold:
        return DetectedFormat.SYSLOG
    if json_hits >= threshold:
        return DetectedFormat.JSONL
    if bracket_hits >= threshold:
        return DetectedFormat.BRACKET
    return DetectedFormat.UNKNOWN


def iter_hits(
    log_path: str | Path,
    *,
    scan: Optional[ScanConfig] = None,
    detected: Optional[DetectedFormat] = None,
    sample_lines: int = 120,
) -> Iterator[LogHit]:
    """Adaptive fast scan based on sniffed format.
    - ACCESS: extract HTTP status -> yield 4xx/5xx
    - SYSLOG: extract PRI -> map severity -> yield WARNING/ERROR/CRITICAL
    - JSONL/BRACKET/UNKNOWN: token scan using ScanConfig
    """
    scan = scan or default_scan_config()

    path = Path(log_path)
    if not path.is_file():
        raise FileNotFoundError(f"Log file not found: {path}")

    fmt = detected or sniff_format(path, sample_lines=sample_lines)

    if fmt == DetectedFormat.ACCESS:
        yield from _iter_access_hits(path)
        return
    if fmt == DetectedFormat.SYSLOG:
        yield from _iter_syslog_hits(path)
        return

    yield from _iter_token_hits(path, scan=scan)


def _iter_access_hits(path: Path) -> Iterator[LogHit]:
    with path.open("rb") as f:
        for line_no, raw in enumerate(f, start=1):
            m = _ACCESS_RE.match(raw)
            if not m:
                continue
            status = int(m.group("status"))
            level = AccessLogParser.level_from_status(status)
            if level in (LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL):
                yield LogHit(line_no=line_no, level=level, raw_line=raw)


def _iter_syslog_hits(path: Path) -> Iterator[LogHit]:
    with path.open("rb") as f:
        for line_no, raw in enumerate(f, start=1):
            m = _SYSLOG_PRI_RE.match(raw)
            if not m:
                continue
            pri = int(m.group("pri"))
            level = SyslogParser.level_from_pri(pri)
            if level in (LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL):
                yield LogHit(line_no=line_no, level=level, raw_line=raw)


def _iter_token_hits(path: Path, *, scan: ScanConfig) -> Iterator[LogHit]:
    with path.open("rb") as f:
        for line_no, raw in enumerate(f, start=1):
            hay = raw.upper() if scan.case_insensitive else raw

            matched_level: Optional[LogLevel] = None
            for level in _SEVERITY_PRIORITY:
                patterns: Optional[Sequence[bytes]] = scan.tokens.get(level)
                if not patterns:
                    continue

                for p in patterns:
                    needle = p.upper() if scan.case_insensitive else p
                    if needle in hay:
                        matched_level = level
                        break

                if matched_level is not None:
                    break

            if matched_level is not None:
                yield LogHit(line_no=line_no, level=matched_level, raw_line=raw)
