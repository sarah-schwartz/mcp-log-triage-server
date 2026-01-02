---
title: Resources
description: Resource URIs exposed by the server.
---

Resources are addressable blobs that clients can fetch by URI.

## Built-in Resources

- `app://log-triage/help`
- `app://log-triage/config/scan-tokens`
- `app://log-triage/schemas/ai-review-response`
- `app://log-triage/examples/sample-log`

## File Resources

`file://{path}` reads a text file from within `LOG_TRIAGE_BASE_DIR`.

Safety constraints:

- Allowed extensions: `.log`, `.txt`, `.md` (and `.gz` variants)
- Paths must stay inside `LOG_TRIAGE_BASE_DIR`

## Log Tail Resource

`log://{path}` returns the full log file contents using the same base directory
rules as `file://{path}`.
