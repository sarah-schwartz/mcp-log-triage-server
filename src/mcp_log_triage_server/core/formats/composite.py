"""Parser composition utilities."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..models import LogEntry
from .base import LogParser


@dataclass(frozen=True, slots=True)
class CompositeParser:
    """Try parsers in order and return the first successful parse."""

    parsers: Sequence[LogParser]

    def parse(self, line_no: int, line: str) -> LogEntry | None:
        """Return the first successful parse from the configured parsers."""
        for p in self.parsers:
            out = p.parse(line_no, line)
            if out is not None:
                return out
        return None
