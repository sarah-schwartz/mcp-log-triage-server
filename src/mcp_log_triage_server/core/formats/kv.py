"""Helpers for key-value log formats."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from ..models import LogLevel

_LEVEL_ALIASES = {
    "WARN": "WARNING",
    "ERR": "ERROR",
    "FATAL": "CRITICAL",
    "CRIT": "CRITICAL",
    "SEVERE": "CRITICAL",
}

TIME_KEYS: Sequence[str] = ("timestamp", "time", "ts", "@timestamp")
LEVEL_KEYS: Sequence[str] = ("level", "severity", "lvl", "log_level")
MESSAGE_KEYS: Sequence[str] = ("message", "msg", "error", "detail")


def parse_iso_timestamp(value: str) -> datetime | None:
    """Parse an ISO8601 timestamp string into a datetime."""
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if ts.tzinfo is not None:
        ts = ts.astimezone(UTC)
    return ts


def parse_level(value: str) -> LogLevel:
    """Parse a string log level into a LogLevel enum."""
    name = value.strip().upper()
    if not name:
        return LogLevel.UNKNOWN
    name = _LEVEL_ALIASES.get(name, name)
    try:
        return LogLevel[name]
    except KeyError:
        return LogLevel.UNKNOWN


def extract_common_fields(
    fields: Mapping[str, str],
    *,
    time_keys: Sequence[str] = TIME_KEYS,
    level_keys: Sequence[str] = LEVEL_KEYS,
    message_keys: Sequence[str] = MESSAGE_KEYS,
) -> tuple[datetime | None, LogLevel, str | None]:
    """Extract timestamp, level, and message from key-value fields."""
    lower = {k.lower(): v for k, v in fields.items()}

    ts: datetime | None = None
    for key in time_keys:
        val = lower.get(key)
        if isinstance(val, str):
            ts = parse_iso_timestamp(val)
            if ts is not None:
                break

    level = LogLevel.UNKNOWN
    for key in level_keys:
        val = lower.get(key)
        if isinstance(val, str):
            level = parse_level(val)
            if level is not LogLevel.UNKNOWN:
                break

    message = None
    for key in message_keys:
        val = lower.get(key)
        if isinstance(val, str) and val:
            message = val
            break

    return ts, level, message
