"""Prompt construction for AI review."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import LogLevel


def build_ai_review_prompt(lines_text: str, *, identified_levels: Iterable[LogLevel]) -> str:
    """Build the Gemini prompt for AI review."""
    levels = ", ".join(
        level.value for level in sorted(set(identified_levels), key=lambda lvl: lvl.value)
    )
    return (
        "You are a log triage assistant.\n"
        f"You will be given application log lines not classified as: {levels}.\n"
        "Identify whether these lines likely indicate a hidden error or incident signal.\n"
        "Return ONLY valid JSON that matches the provided schema.\n"
        "Rules:\n"
        "- Only use evidence from the given lines.\n"
        "- Reference line_numbers only from the provided lines.\n"
        "- Prefer fewer, higher-quality findings.\n"
        "- If nothing looks like an incident, return an empty findings array.\n\n"
        f"LOG LINES:\n{lines_text}\n"
    )
