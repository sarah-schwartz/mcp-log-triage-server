---
title: CLI
description: Command-line entrypoints.
---

## Stdio Server

```bash
python -m mcp_log_triage_server
```

Or via the console script:

```bash
log-triage-mcp
```

These start a stdio MCP server. The process reads and writes over stdin/stdout,
so it is designed to be launched by an MCP-compatible client.

## Environment Overrides

- `LOG_TRIAGE_LOG_LEVEL` controls verbosity
- `LOG_TRIAGE_BASE_DIR` scopes file/log resource access

## Notes

There are no CLI flags; configuration is done via environment variables and
tool inputs.
