---
title: Testing
description: Test strategy and patterns.
---

## Run Tests

```bash
pytest -q
```

## Test Organization

Tests mirror the `src/` structure. For example:

- `src/mcp_log_triage_server/core/log_service.py`
- `tests/core/test_log_service.py`

## Guidelines

- One behavior per test for clear failures.
- Use `tmp_path` to create log files in isolation.
- Mark async tests with `@pytest.mark.asyncio`.
- Avoid network calls and external services in unit tests.
- Prefer deterministic timestamps and explicit windows in time-based tests.

## Coverage Focus

- Time window parsing and validation
- Format detection and parser correctness
- Prefilter behavior on large logs
- Tool input validation and response shape
