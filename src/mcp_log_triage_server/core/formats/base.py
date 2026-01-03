"""Parser interfaces and scan configuration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ..models import LogEntry, LogLevel


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
