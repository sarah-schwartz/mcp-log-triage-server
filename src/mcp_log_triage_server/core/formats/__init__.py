"""Log parsing formats and scan configuration.

Contains parsers for common log formats (JSON lines, syslog, access logs, etc.).
"""

from __future__ import annotations

from .access import AccessLogParser
from .base import LogParser, ScanConfig, default_scan_config
from .bracket import BracketTimestampParser
from .cef import CefParser
from .composite import CompositeParser
from .jsonl import JsonLinesParser
from .logfmt import LogfmtParser
from .loose import LooseLevelParser
from .ltsv import LtsvParser
from .syslog import SyslogParser

__all__ = [
    "AccessLogParser",
    "BracketTimestampParser",
    "CefParser",
    "CompositeParser",
    "JsonLinesParser",
    "LogParser",
    "LogfmtParser",
    "LooseLevelParser",
    "LtsvParser",
    "ScanConfig",
    "SyslogParser",
    "default_scan_config",
]
