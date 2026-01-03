"""CEF (Common Event Format) parser."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ..models import LogEntry, LogLevel
from .kv import extract_common_fields

_CEF_PREFIX = "CEF:"


def _map_cef_severity(value: str) -> LogLevel:
    try:
        sev = int(value)
    except ValueError:
        return LogLevel.UNKNOWN

    if sev <= 3:
        return LogLevel.INFO
    if sev <= 6:
        return LogLevel.WARNING
    if sev <= 8:
        return LogLevel.ERROR
    return LogLevel.CRITICAL


def _parse_extension(ext: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for token in ext.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if not key:
            continue
        fields[key] = value
    return fields


@dataclass(frozen=True, slots=True)
class CefParser:
    """Parse CEF header and extension fields."""

    def parse(self, line_no: int, line: str) -> LogEntry | None:
        """Parse a CEF line into a LogEntry."""
        if not line.startswith(_CEF_PREFIX):
            return None

        parts = line.split("|", 7)
        if len(parts) < 7:
            return None

        version = parts[0][len(_CEF_PREFIX) :]
        device_vendor = parts[1]
        device_product = parts[2]
        device_version = parts[3]
        signature_id = parts[4]
        name = parts[5]
        severity_raw = parts[6]
        extension_raw = parts[7] if len(parts) > 7 else ""

        extension = _parse_extension(extension_raw)
        ts, _, message = extract_common_fields(extension)
        if ts is None:
            rt = extension.get("rt")
            if rt and rt.isdigit():
                ms = int(rt)
                ts = datetime.fromtimestamp(ms / 1000.0, tz=UTC)

        level = _map_cef_severity(severity_raw)
        msg = message or name or line.strip()

        return LogEntry(
            line_no=line_no,
            timestamp=ts,
            level=level,
            message=msg,
            raw=line,
            meta={
                "cef": {
                    "version": version,
                    "device_vendor": device_vendor,
                    "device_product": device_product,
                    "device_version": device_version,
                    "signature_id": signature_id,
                    "name": name,
                    "severity": severity_raw,
                    "extension": extension,
                }
            },
        )
