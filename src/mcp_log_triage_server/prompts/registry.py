"""MCP prompt registry.

Prompts are predefined conversation/workflow templates that the client can invoke explicitly.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP


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
        levels: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Build a prompt for structured log triage."""
        if levels is None:
            levels = ["error", "warning", "critical"]
        return [
            {
                "role": "system",
                "content": (
                    "You triage application logs. "
                    "Use tools when helpful, and write a structured incident-style summary."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Please triage the log file and produce:\n"
                    "1) What happened (1-3 bullets)\n"
                    "2) Evidence (quote key lines)\n"
                    "3) Suspected root cause\n"
                    "4) Next actions\n\n"
                    f"Use tool triage_logs with:\n"
                    f"- log_path: {log_path}\n"
                    f"- hours_lookback: {hours_lookback}\n"
                    f"- levels: {levels}\n"
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "If you need extra context, you can read the tail via:",
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
