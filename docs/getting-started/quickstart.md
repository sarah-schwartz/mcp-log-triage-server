---
title: Quickstart
description: Run the server and make your first tool call.
---

## Run the Server (stdio)

```bash
python -m mcp_log_triage_server
```

Or via the console script:

```bash
log-triage-mcp
```

## Call the Tool

The server exposes a single tool named `triage_logs`. Example payload:

```json
{
  "log_path": "samples/access.log",
  "date": "2025-12-31",
  "levels": ["error", "critical"],
  "limit": 200
}
```

## Next Steps

- Learn the full tool API in `docs/guides/tools.md`
- Review resources and prompts in `docs/guides/resources.md` and
  `docs/guides/prompts.md`
- Configure base paths and log levels in `docs/reference/configuration.md`
