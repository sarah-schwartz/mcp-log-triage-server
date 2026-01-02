---
title: Prompts
description: Prompt templates exposed by the server.
---

Prompts are reusable conversation templates that a client can invoke.

## Available Prompts

- `summarize_resource(uri)`
  - Summarizes a resource by URI.
- `triage_log_file(log_path, hours_lookback=24, levels="ERROR,WARNING,CRITICAL", limit=200)`
  - Guides a user through log triage with a structured summary.
- `create_bug_report(title, log_path, steps="", hours_lookback=24)`
  - Produces a Markdown bug report using log evidence.

Prompts return lists of role/content messages that the MCP client can forward
to an LLM.
