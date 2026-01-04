---
title: Resources
description: Resource URIs exposed by the server.
---

Resources are addressable blobs that clients can fetch by URI. They are useful
for sharing configuration hints, schemas, or sample data without invoking tools.

## Built-in Resources

- `app://log-triage/help`
- `app://log-triage/config/scan-tokens`
- `app://log-triage/schemas/ai-review-response`
- `app://log-triage/examples/sample-log`

Each built-in URI returns a small text or JSON payload. These are lightweight
and safe for repeated calls.

## File Resources

`file://{path}` reads a text file from within `LOG_TRIAGE_BASE_DIR`.

Safety constraints:

- Allowed extensions: `.log`, `.txt`, `.md` (and `.gz` variants)
- Paths must stay inside `LOG_TRIAGE_BASE_DIR`

Example:

```
file://samples/access.log
```

## Log Tail Resource

`log://{path}` returns the full log file contents using the same base directory
and allowlist rules as `file://{path}` (including `.gz` for allowed suffixes).

Example:

```
log://samples/syslog.log
```
