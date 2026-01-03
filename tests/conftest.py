from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def write_bracket_log() -> Callable[[Path], None]:
    def _write(path: Path) -> None:
        path.write_text(
            "\n".join(
                [
                    "2025-12-30 08:00:00 [INFO] start",
                    "2025-12-30 09:00:00 [WARNING] warn",
                    "2025-12-30 10:00:00 [ERROR] err",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    return _write


@pytest.fixture
def write_log() -> Callable[[Path], None]:
    def _write(path: Path) -> None:
        path.write_text(
            "\n".join(
                [
                    "2025-12-30T08:12:01Z [INFO] service started",
                    "2025-12-30T08:12:03Z [WARNING] retrying request id=abc123",
                    "2025-12-30T08:12:04Z [ERROR] upstream timeout route=/api/v1/items",
                    "2025-12-30T08:12:05Z [CRITICAL] database unavailable",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    return _write


@pytest.fixture
def write_bytes() -> Callable[[Path, list[bytes]], None]:
    def _write(path: Path, lines: list[bytes]) -> None:
        path.write_bytes(b"".join(line + b"\n" for line in lines))

    return _write
