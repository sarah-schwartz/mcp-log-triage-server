# mcp_server.py
from __future__ import annotations

import logging
import re
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal, Optional, Sequence

from mcp.server.fastmcp import FastMCP

from mcp_log_triage_server.log_service import default_parser, get_logs
from mcp_log_triage_server.models import LogEntry, LogLevel

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

_WEEK_RE = re.compile(r"^(?P<y>\d{4})-W(?P<w>\d{2})$")
_MONTH_RE = re.compile(r"^(?P<y>\d{4})-(?P<m>\d{2})$")
_HOUR_RE = re.compile(r"^(?P<d>\d{4}-\d{2}-\d{2})T(?P<h>\d{2})$")

mcp = FastMCP("log-triage", json_response=True)


def _parse_levels(levels: Optional[Sequence[str]]) -> list[LogLevel]:
    if not levels:
        return [LogLevel.ERROR, LogLevel.WARNING, LogLevel.CRITICAL]

    out: list[LogLevel] = []
    for s in levels:
        name = (s or "").strip().upper()
        if not name:
            continue
        try:
            out.append(LogLevel(name))
        except ValueError as e:
            raise ValueError(
                "Invalid level. Allowed: CRITICAL, ERROR, WARNING, INFO, DEBUG, UNKNOWN"
            ) from e

    if not out:
        raise ValueError("At least one level must be provided")
    return out


def _parse_iso_dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _range_for_date(s: str) -> tuple[datetime, datetime]:
    d = date.fromisoformat(s)
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def _range_for_hour(s: str) -> tuple[datetime, datetime]:
    # Accepts YYYY-MM-DDTHH (no minutes) for ergonomics.
    m = _HOUR_RE.match(s)
    if not m:
        raise ValueError("hour must look like YYYY-MM-DDTHH (e.g., 2025-12-29T10)")
    d = date.fromisoformat(m.group("d"))
    h = int(m.group("h"))
    start = datetime(d.year, d.month, d.day, h, tzinfo=timezone.utc)
    return start, start + timedelta(hours=1)


def _range_for_week(s: str) -> tuple[datetime, datetime]:
    m = _WEEK_RE.match(s)
    if not m:
        raise ValueError("week must look like YYYY-Www (e.g., 2025-W52)")
    y = int(m.group("y"))
    w = int(m.group("w"))
    start_date = date.fromisocalendar(y, w, 1)  # Monday
    start = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=7)


def _range_for_month(s: str) -> tuple[datetime, datetime]:
    m = _MONTH_RE.match(s)
    if not m:
        raise ValueError("month must look like YYYY-MM (e.g., 2025-12)")
    y = int(m.group("y"))
    mo = int(m.group("m"))
    start = datetime(y, mo, 1, tzinfo=timezone.utc)
    end = datetime(y + 1, 1, 1, tzinfo=timezone.utc) if mo == 12 else datetime(y, mo + 1, 1, tzinfo=timezone.utc)
    return start, end


def _resolve_time_window(
    *,
    since: Optional[str],
    until: Optional[str],
    date_: Optional[str],
    hour: Optional[str],
    week: Optional[str],
    month: Optional[str],
) -> tuple[Optional[datetime], Optional[datetime]]:
    if date_:
        return _range_for_date(date_)
    if hour:
        return _range_for_hour(hour)
    if week:
        return _range_for_week(week)
    if month:
        return _range_for_month(month)

    s = _parse_iso_dt(since) if since else None
    u = _parse_iso_dt(until) if until else None
    return s, u


def _entry_to_dict(e: LogEntry, *, include_raw: bool) -> dict[str, Any]:
    return {
        "line_no": e.line_no,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "level": e.level.value,
        "message": e.message,
        "raw": e.raw if include_raw else None,
        "meta": e.meta,
    }


@mcp.tool()
def triage_logs(
    log_path: str,
    levels: Optional[list[str]] = None,
    max_results: int = 200,
    fast_prefilter: bool = True,
    sniff_lines: int = 120,
    timestamp_policy: Literal["include", "exclude"] = "include",
    include_raw: bool = False,
    hours_lookback: int = 24,
    since: Optional[str] = None,
    until: Optional[str] = None,
    date: Optional[str] = None,
    hour: Optional[str] = None,
    week: Optional[str] = None,
    month: Optional[str] = None,
) -> dict[str, Any]:
    # stdout must remain clean for stdio transport.
    sev = _parse_levels(levels)
    window_since, window_until = _resolve_time_window(
        since=since, until=until, date_=date, hour=hour, week=week, month=month
    )
    effective_lookback = None if (window_since is not None or window_until is not None) else hours_lookback

    entries = get_logs(
        log_path,
        hours_lookback=effective_lookback,
        since=window_since,
        until=window_until,
        severities=sev,
        max_results=max_results,
        fast_prefilter=fast_prefilter,
        parser=default_parser(),
        timestamp_policy=timestamp_policy,
        sniff_lines=sniff_lines,
        include_raw=include_raw,
    )

    return {
        "count": len(entries),
        "entries": [_entry_to_dict(e, include_raw=include_raw) for e in entries],
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
