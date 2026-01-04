---
title: Prompts
description: Prompt templates exposed by the server.
---

Prompts are reusable conversation templates that a client can invoke. They
return a list of role/content messages suitable for an MCP client to forward
to an LLM.

## Available Prompts

- `summarize_resource(uri)`
  - Summarizes a resource by URI with key points, risks, and actionable items.
  - If the resource is code, summarizes its purpose and main interfaces.
- `triage_log_file(log_path, hours_lookback=24, levels=["ERROR","WARNING","CRITICAL"], since=None, until=None, date=None, hour=None, week=None, month=None, year=None, days_lookback=None)`
  - Guides a user through log triage with a structured summary.
  - Encourages evidence-based reporting and next steps with line references.
  - Accepts one time window selector at a time (date/hour/week/month/year, since/until, or days_lookback/hours_lookback).
- `create_bug_report(title, log_path, steps="", hours_lookback=24)`
  - Produces a Markdown bug report using log evidence, redacting sensitive data.
  - Accepts optional steps to reproduce for completeness.

Prompts return lists of role/content messages that the MCP client can forward
to an LLM.

## Example Usage

If your client supports prompt invocation, call the prompt by name with the
required arguments and then pass the returned messages to the model.
