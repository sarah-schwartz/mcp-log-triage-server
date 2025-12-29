from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Iterable, Iterator, Optional

from mcp_log_triage_server.formats import (
    AccessLogParser,
    BracketTimestampParser,
    CompositeParser,
    JsonLinesParser,
    LogParser,
    LooseLevelParser,
    ScanConfig,
    SyslogParser,
    default_scan_config,
)
from mcp_log_triage_server.models import LogEntry, LogLevel
from mcp_log_triage_server.scanning import DetectedFormat, iter_hits, sniff_format


def default_parser() -> LogParser:
    """Default parser chain (first match wins)."""
    return CompositeParser(
        parsers=[
            SyslogParser(),
            AccessLogParser(),
            BracketTimestampParser(
                timestamp_formats=(
                    "%Y-%m-%d %H:%M:%S",
                    "%Y/%m/%d %H:%M:%S",
                    "%d-%m-%Y %H:%M:%S",
                )
            ),
            JsonLinesParser(),
            LooseLevelParser(),
        ]
    )


def _normalize_ts(ts: datetime, *, default_tz: tzinfo) -> datetime:
    """Normalize timestamps to timezone-aware UTC."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=default_tz)
    return ts.astimezone(timezone.utc)


def _drop_raw(entry: LogEntry) -> LogEntry:
    return LogEntry(
        line_no=entry.line_no,
        timestamp=entry.timestamp,
        level=entry.level,
        message=entry.message,
        raw=None,
        meta=entry.meta,
    )


def iter_entries(
    log_path: str | Path,
    *,
    parser: Optional[LogParser] = None,
    scan: Optional[ScanConfig] = None,
    hours_lookback: int = 24,
    severities: Optional[Iterable[LogLevel]] = None,
    default_tz: tzinfo = timezone.utc,
    encoding: str = "utf-8",
    decode_errors: str = "replace",
    fast_prefilter: bool = True,
    timestamp_policy: str = "include",  # "include" | "exclude" when timestamp is None
    sniff_lines: int = 120,
    include_raw: bool = True,
) -> Iterator[LogEntry]:
    """Yield parsed entries after optional fast prefilter + filters."""
    path = Path(log_path)
    if not path.is_file():
        raise FileNotFoundError(f"Log file not found: {path}")
    if hours_lookback < 0:
        raise ValueError("hours_lookback must be >= 0")
    if timestamp_policy not in ("include", "exclude"):
        raise ValueError("timestamp_policy must be 'include' or 'exclude'")

    parser = parser or default_parser()
    scan = scan or default_scan_config()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)

    allowed: Optional[set[LogLevel]] = None
    if severities is not None:
        allowed = set(severities)
        if not allowed:
            return

    def time_ok(e: LogEntry) -> bool:
        if e.timestamp is None:
            return timestamp_policy == "include"
        return _normalize_ts(e.timestamp, default_tz=default_tz) >= cutoff

    detected = sniff_format(path, sample_lines=sniff_lines)

    # Fast path: scan candidates first when format is recognized
    if fast_prefilter and detected != DetectedFormat.UNKNOWN:
        for hit in iter_hits(path, scan=scan, detected=detected, sample_lines=sniff_lines):
            line = hit.raw_line.decode(encoding, errors=decode_errors).rstrip("\r\n")
            entry = parser.parse(hit.line_no, line)

            if entry is None:
                entry = LogEntry(
                    line_no=hit.line_no,
                    timestamp=None,
                    level=hit.level,
                    message=line.strip(),
                    raw=(line if include_raw else None),
                )
            else:
                if not include_raw:
                    entry = _drop_raw(entry)

            if allowed is not None and entry.level not in allowed:
                continue
            if not time_ok(entry):
                continue

            yield entry
        return

    # Slow path: parse every line (max compatibility)
    with path.open("r", encoding=encoding, errors=decode_errors) as f:
        for line_no, line in enumerate(f, start=1):
            line = line.rstrip("\r\n")
            entry = parser.parse(line_no, line)
            if entry is None:
                continue

            if not include_raw:
                entry = _drop_raw(entry)

            if allowed is not None and entry.level not in allowed:
                continue
            if not time_ok(entry):
                continue

            yield entry


def get_logs(
    log_path: str | Path,
    *,
    max_results: Optional[int] = None,
    **iter_kwargs,
) -> list[LogEntry]:
    """Collect iter_entries into a list (optionally capped)."""
    if max_results is not None and max_results <= 0:
        raise ValueError("max_results must be > 0")

    it = iter_entries(log_path, **iter_kwargs)

    if max_results is None:
        return list(it)

    buf: deque[LogEntry] = deque(maxlen=max_results)
    for entry in it:
        buf.append(entry)
    return list(buf)
