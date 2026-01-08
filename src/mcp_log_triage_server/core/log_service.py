"""Log loading, filtering and iteration utilities.

This module is the main integration point that reads log files and returns normalized entries.
"""

from __future__ import annotations

import gzip
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta, tzinfo
from pathlib import Path

import aiofiles
from aiofiles.threadpool import wrap

from .formats import (
    AccessLogParser,
    BracketTimestampParser,
    CefParser,
    CompositeParser,
    JsonLinesParser,
    LogfmtParser,
    LogParser,
    LooseLevelParser,
    LtsvParser,
    ScanConfig,
    SyslogParser,
    default_scan_config,
)
from .models import LogEntry, LogLevel
from .scanning import DetectedFormat, iter_hits, sniff_format


@asynccontextmanager
async def _open_text(path: Path, *, encoding: str, decode_errors: str):
    """Open a log file for async text reading (plain or gzip)."""
    if path.suffix.lower() == ".gz":
        f = gzip.open(path, mode="rt", encoding=encoding, errors=decode_errors)
        af = wrap(f)
        try:
            yield af
        finally:
            await af.close()
    else:
        async with aiofiles.open(path, mode="r", encoding=encoding, errors=decode_errors) as f:
            yield f


def default_parser() -> LogParser:
    """Default parser chain (first match wins)."""
    return CompositeParser(
        parsers=[
            SyslogParser(),
            AccessLogParser(),
            BracketTimestampParser(
                timestamp_formats=(
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y/%m/%d %H:%M:%S",
                    "%d-%m-%Y %H:%M:%S",
                )
            ),
            JsonLinesParser(),
            CefParser(),
            LogfmtParser(),
            LtsvParser(),
            LooseLevelParser(),
        ]
    )


def _normalize_ts(ts: datetime, *, default_tz: tzinfo) -> datetime:
    """Normalize timestamps to timezone-aware UTC."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=default_tz)
    return ts.astimezone(UTC)


def _normalize_window(
    *,
    since: datetime | None,
    until: datetime | None,
    default_tz: tzinfo,
) -> tuple[datetime | None, datetime | None]:
    """Normalize a [since, until) window into UTC."""
    if since is not None:
        since = _normalize_ts(since, default_tz=default_tz)
    if until is not None:
        until = _normalize_ts(until, default_tz=default_tz)

    if since is not None and until is not None and since >= until:
        raise ValueError("since must be < until")

    return since, until


def _drop_raw(entry: LogEntry) -> LogEntry:
    """Return a copy of the entry without raw payload."""
    return LogEntry(
        line_no=entry.line_no,
        timestamp=entry.timestamp,
        level=entry.level,
        message=entry.message,
        raw=None,
        meta=entry.meta,
    )


async def iter_entries(
    log_path: str | Path,
    *,
    parser: LogParser | None = None,
    scan: ScanConfig | None = None,
    # Backwards-compatible option:
    # if since/until are not provided, we can use lookback.
    hours_lookback: int | None = 24,
    # Preferred: explicit time window (UTC-normalized)
    since: datetime | None = None,
    until: datetime | None = None,
    severities: Iterable[LogLevel] | None = None,
    contains: str | None = None,
    default_tz: tzinfo = UTC,
    encoding: str = "utf-8",
    decode_errors: str = "replace",
    fast_prefilter: bool = True,
    timestamp_policy: str = "include",  # include|exclude when timestamp is None
    sniff_lines: int = 120,
    include_raw: bool = True,
) -> AsyncIterator[LogEntry]:
    """Yield parsed entries after optional prefiltering and filtering."""
    path = Path(log_path)
    if not path.is_file():
        raise FileNotFoundError(f"Log file not found: {path}")
    if timestamp_policy not in ("include", "exclude"):
        raise ValueError("timestamp_policy must be 'include' or 'exclude'")

    # Avoid ambiguous behavior: either a window or lookback, not both.
    if (since is not None or until is not None) and hours_lookback is not None:
        raise ValueError("Use either (since/until) OR hours_lookback, not both.")

    parser = parser or default_parser()
    scan = scan or default_scan_config()

    # Derive a window from lookback if no window was provided.
    if since is None and until is None and hours_lookback is not None:
        if hours_lookback < 0:
            raise ValueError("hours_lookback must be >= 0")
        until = datetime.now(UTC)
        since = until - timedelta(hours=hours_lookback)

    since, until = _normalize_window(since=since, until=until, default_tz=default_tz)

    allowed: set[LogLevel] | None = None
    if severities is not None:
        allowed = set(severities)
        if not allowed:
            return

    # Precompute bytes filter to avoid decoding in the fast path.
    contains_b: bytes | None = None
    if contains is not None:
        contains_b = contains.encode(encoding, errors="ignore")

    def time_ok(e: LogEntry) -> bool:
        if e.timestamp is None:
            return timestamp_policy == "include"

        ts = _normalize_ts(e.timestamp, default_tz=default_tz)

        if since is not None and ts < since:
            return False
        if until is not None and ts >= until:
            return False
        return True

    detected = await sniff_format(path, sample_lines=sniff_lines)

    # Fast path: scan candidates first only when format is recognized.
    if fast_prefilter and detected != DetectedFormat.UNKNOWN:
        async for hit in iter_hits(path, scan=scan, detected=detected, sample_lines=sniff_lines):
            # Filter by bytes before decoding to save work on large logs.
            if contains_b is not None and contains_b not in hit.raw_line:
                continue

            line = hit.raw_line.decode(encoding, errors=decode_errors).rstrip("\r\n")

            entry = parser.parse(hit.line_no, line)
            if entry is None:
                entry = LogEntry(
                    line_no=hit.line_no,
                    timestamp=None,
                    level=hit.level,
                    message=line.strip(),
                    raw=(line if include_raw else None),
                    meta=None,
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

    # Slow path: parse every line (max compatibility).
    async with _open_text(path, encoding=encoding, decode_errors=decode_errors) as f:
        async for line_no, line in _enumerate_async(f, start=1):
            line = line.rstrip("\r\n")
            if contains is not None and contains not in line:
                continue
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


async def get_logs(
    log_path: str | Path,
    **iter_kwargs,
) -> list[LogEntry]:
    """Collect iter_entries into a list."""
    return [entry async for entry in iter_entries(log_path, **iter_kwargs)]


async def _enumerate_async(iterable, start: int = 0):
    """Async enumerate helper for async iterators."""
    index = start
    async for item in iterable:
        yield index, item
        index += 1
