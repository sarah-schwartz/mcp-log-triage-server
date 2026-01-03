from __future__ import annotations

from pathlib import Path

import pytest

from mcp_log_triage_server.core import ai_review as ai_module
from mcp_log_triage_server.core.ai_review import AIFinding, AIReviewResponse
from mcp_log_triage_server.tools.triage import triage_logs_impl


def _write_log(path: Path) -> None:
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


def test_triage_logs_impl_filters_levels_and_contains(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    _write_log(log)

    out = triage_logs_impl(
        log_path=str(log),
        date="2025-12-30",
        levels=["error", "critical"],
        contains="route=",
        include_raw=False,
    )

    assert out["count"] == 1
    entry = out["entries"][0]
    assert entry["level"] == "error"
    assert "route=/api/v1/items" in entry["message"]
    assert "raw" not in entry


def test_triage_logs_impl_year_selector(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    log.write_text(
        "\n".join(
            [
                "2024-12-31T23:59:59Z [ERROR] last year",
                "2025-01-01T00:00:00Z [ERROR] new year",
                "2025-12-31T23:59:59Z [ERROR] end year",
                "2026-01-01T00:00:00Z [ERROR] next year",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    out = triage_logs_impl(
        log_path=str(log),
        year="2025",
        include_all_levels=True,
    )

    assert out["count"] == 2


def test_triage_logs_impl_include_all_levels_overrides_levels(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    _write_log(log)

    out = triage_logs_impl(
        log_path=str(log),
        date="2025-12-30",
        levels=["error"],
        include_all_levels=True,
    )

    assert out["count"] == 4


def test_triage_logs_impl_invalid_level(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    _write_log(log)

    with pytest.raises(ValueError):
        triage_logs_impl(
            log_path=str(log),
            date="2025-12-30",
            levels=["not-a-level"],
        )


def test_triage_logs_impl_include_raw(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    _write_log(log)

    out = triage_logs_impl(
        log_path=str(log),
        date="2025-12-30",
        levels=["error"],
        include_raw=True,
    )

    assert out["count"] == 1
    assert "raw" in out["entries"][0]


def test_triage_logs_impl_include_ai_review(tmp_path: Path, monkeypatch) -> None:
    log = tmp_path / "app.log"
    _write_log(log)

    def fake_call(prompt: str, *, cfg) -> AIReviewResponse:
        return AIReviewResponse(
            findings=[
                AIFinding(
                    line_numbers=[1],
                    severity_guess="low",
                    confidence=0.6,
                    title="Test",
                    rationale="Test",
                    recommendation="Test",
                )
            ]
        )

    monkeypatch.setattr(ai_module, "_call_gemini_json", fake_call)

    out = triage_logs_impl(
        log_path=str(log),
        date="2025-12-30",
        include_ai_review=True,
    )

    assert out["count"] == 3
    assert "ai_findings" in out
    assert out["ai_findings"][0]["title"] == "Test"


def test_triage_logs_impl_include_ai_review_conflicts(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    _write_log(log)

    with pytest.raises(ValueError):
        triage_logs_impl(
            log_path=str(log),
            date="2025-12-30",
            include_ai_review=True,
            include_all_levels=True,
        )


def test_triage_logs_impl_ignores_limit(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    _write_log(log)

    out = triage_logs_impl(
        log_path=str(log),
        date="2025-12-30",
        limit=1,
    )

    assert out["count"] == 2
