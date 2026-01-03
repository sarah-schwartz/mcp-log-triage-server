"""Log parsing formats and scan configuration.

Contains parsers for common log formats (JSON lines, syslog, access logs, etc.).
"""

from __future__ import annotations

from .access import AccessLogParser
from .base import LogParser, ScanConfig, default_scan_config
from .bracket import BracketTimestampParser
from .composite import CompositeParser
from .jsonl import JsonLinesParser
from .loose import LooseLevelParser
from .syslog import SyslogParser

__all__ = [
    "AccessLogParser",
    "BracketTimestampParser",
    "CompositeParser",
    "JsonLinesParser",
    "LogParser",
    "LooseLevelParser",
    "ScanConfig",
    "SyslogParser",
    "default_scan_config",
]
