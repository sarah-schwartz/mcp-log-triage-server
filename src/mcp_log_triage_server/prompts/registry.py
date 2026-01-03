"""MCP prompt registry.

Prompts are predefined conversation/workflow templates that the client can invoke explicitly.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mcp.server.fastmcp import FastMCP


def _format_levels(levels: str | Sequence[str]) -> str:
    """Return levels as a JSON-like list string for prompt display."""
    if isinstance(levels, str):
        items = [s.strip().upper() for s in levels.split(",") if s.strip()]
    else:
        items = [str(s).strip().upper() for s in levels if str(s).strip()]
    if not items:
        return "[]"
    quoted = ", ".join(f'"{item}"' for item in items)
    return f"[{quoted}]"


def register_prompts(mcp: FastMCP) -> None:
    """Register prompt templates on the MCP server."""

    @mcp.prompt()
    def summarize_resource(uri: str) -> list[dict[str, Any]]:
        """Build a prompt that summarizes a resource URI."""
        return [
            {
                "role": "system",
                "content": (
                    "You are a precise assistant. Summarize the provided resource clearly and "
                    "concisely."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Summarize this resource:"},
                    {"type": "resource", "uri": uri},
                ],
            },
        ]

    @mcp.prompt()
    def triage_log_file(
        log_path: str,
        hours_lookback: int = 24,
        levels: str = "ERROR,WARNING,CRITICAL",
    ) -> list[dict[str, Any]]:
        """Build a prompt for structured log triage."""
        levels_display = _format_levels(levels)
        return [
            {
                "role": "system",
                "content": (
                    "You are a senior incident triage assistant for backend services. "
                    "Provide concise, evidence-based summaries from log data. "
                    "Do not invent details; if the evidence is insufficient, say so."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Triage the log file using triage_logs. Follow this workflow:\n"
                    "- Always call triage_logs first with the parameters below. "
                    "Set include_raw to true so evidence can be quoted.\n"
                    "- If no entries are returned, state that clearly and suggest "
                    "widening the time window or levels.\n"
                    "- Use only tool output or the log resource for evidence; do not fabricate lines.\n"
                    "- Keep the response concise and incident-focused.\n\n"
                    "Call triage_logs with:\n"
                    f"- log_path: {log_path}\n"
                    f"- hours_lookback: {hours_lookback}\n"
                    f"- levels: {levels_display}\n"
                    "- include_raw: true\n\n"
                    "Return this structure:\n"
                    "1) What happened (1-3 bullets)\n"
                    "2) Evidence (2-5 quoted lines with timestamps/levels)\n"
                    "3) Suspected root cause (1-2 sentences; say 'Unknown' if unclear)\n"
                    "4) Next actions (2-4 bullets)\n"
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Optional: if you need raw context, you can read the log via:",
                    },
                    {"type": "resource", "uri": f"log://{log_path}"},
                ],
            },
        ]

    @mcp.prompt()
    def create_bug_report(
        title: str,
        log_path: str,
        steps: str = "",
        hours_lookback: int = 24,
    ) -> list[dict[str, Any]]:
        """Build a prompt that produces a Markdown bug report."""
        return [
            {
                "role": "system",
                "content": "Create a high-quality bug report in Markdown.",
            },
            {
                "role": "user",
                "content": (
                    f"Title: {title}\n\n"
                    "Please create a bug report with sections:\n"
                    "- Summary\n"
                    "- Environment (if missing, say 'unknown')\n"
                    "- Steps to Reproduce\n"
                    "- Expected vs Actual\n"
                    "- Evidence (from logs)\n"
                    "- Suspected Cause\n"
                    "- Suggested Fix / Next Actions\n\n"
                    f"Steps provided:\n{steps}\n\n"
                    f"Use tool triage_logs on {log_path} for last {hours_lookback} hours.\n"
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "You may also cite lines from the log tail:",
                    },
                    {"type": "resource", "uri": f"log://{log_path}"},
                ],
            },
        ]
