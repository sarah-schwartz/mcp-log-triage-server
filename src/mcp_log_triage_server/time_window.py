from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple

_WEEK_RE = re.compile(r"^(?P<y>\d{4})-W(?P<w>\d{2})$")
_MONTH_RE = re.compile(r"^(?P<y>\d{4})-(?P<m>\d{2})$")


def parse_iso_dt(s: str) -> datetime:
    """Parse ISO8601 datetime. If tz is missing, assume UTC."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def range_for_date(s: str) -> tuple[datetime, datetime]:
    d = date.fromisoformat(s)
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def range_for_hour(s: str) -> tuple[datetime, datetime]:
    # Format: YYYY-MM-DDTHH  (e.g., 2025-12-29T10)
    base = datetime.fromisoformat(s)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    start = base.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    return start, end


def range_for_week(s: str) -> tuple[datetime, datetime]:
    m = _WEEK_RE.match(s)
    if not m:
        raise ValueError("week must look like YYYY-Www (e.g., 2025-W52)")
    y = int(m.group("y"))
    w = int(m.group("w"))
    start_date = date.fromisocalendar(y, w, 1)  # Monday
    start = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    end = start + timedelta(days=7)
    return start, end


def range_for_month(s: str) -> tuple[datetime, datetime]:
    m = _MONTH_RE.match(s)
    if not m:
        raise ValueError("month must look like YYYY-MM (e.g., 2025-12)")
    y = int(m.group("y"))
    mo = int(m.group("m"))
    start = datetime(y, mo, 1, tzinfo=timezone.utc)
    if mo == 12:
        end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(y, mo + 1, 1, tzinfo=timezone.utc)
    return start, end


def resolve_time_window(
    *,
    since: Optional[str] = None,
    until: Optional[str] = None,
    date_: Optional[str] = None,
    hour: Optional[str] = None,
    week: Optional[str] = None,
    month: Optional[str] = None,
) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    Resolve a time window [since, until) in UTC.
    Priority: date/hour/week/month > since/until > none.
    """
    if date_:
        return range_for_date(date_)
    if hour:
        return range_for_hour(hour)
    if week:
        return range_for_week(week)
    if month:
        return range_for_month(month)

    s = parse_iso_dt(since) if since else None
    u = parse_iso_dt(until) if until else None
    return s, u
