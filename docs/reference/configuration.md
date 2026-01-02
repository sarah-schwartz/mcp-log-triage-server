---
title: Configuration
description: Environment variables and defaults.
---

## Environment Variables

- `LOG_TRIAGE_LOG_LEVEL`
  - Default: `INFO`
  - Sets the server log level.

- `LOG_TRIAGE_BASE_DIR`
  - Default: current working directory
  - Base directory for `file://{path}` and `log://{path}` resources.

- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
  - Required only for the AI review pipeline.
