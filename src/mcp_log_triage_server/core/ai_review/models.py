"""AI review models and configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from ..models import LogEntry, LogLevel


class AIFinding(BaseModel):
    line_numbers: list[int] = Field(description="Relevant log line numbers.")
    severity_guess: Literal["low", "medium", "high"] = Field(
        description="Estimated incident severity."
    )
    confidence: float = Field(ge=0.0, le=1.0, description="0..1 confidence for this finding.")
    title: str = Field(description="Short title of the suspected issue.")
    rationale: str = Field(description="Why these lines may indicate an error/incident.")
    recommendation: str = Field(description="Next debugging step to confirm or mitigate.")


class AIReviewResponse(BaseModel):
    findings: list[AIFinding] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AIReviewConfig:
    model: str = "gemini-2.5-flash-lite"
    segment_max_lines: int = 40

    # Local-identified (not sent to AI)
    identified_levels: tuple[LogLevel, ...] = (
        LogLevel.ERROR,
        LogLevel.WARNING,
        LogLevel.CRITICAL,
    )

    # Levels that are sent to the AI review stage.
    ai_levels: tuple[LogLevel, ...] = (
        LogLevel.INFO,
        LogLevel.DEBUG,
        LogLevel.UNKNOWN,
    )

    min_confidence: float = 0.55
    temperature: float = 0.0
    redact: bool = True
    max_retries: int = 3
    max_concurrent_requests: int = 3


@dataclass(frozen=True, slots=True)
class AITriageResult:
    """Split output for local triage + AI findings."""

    identified_entries: list[LogEntry]
    ai_review: AIReviewResponse
