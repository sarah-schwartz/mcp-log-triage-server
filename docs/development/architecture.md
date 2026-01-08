---
title: Architecture
description: Module layout and data flow.
---

## Layers

- `core/`: parsing, filtering, scanning, time-window resolution
- `tools/`: thin adapters that validate inputs and call `core/`
- `resources/`: URI-addressable data exposed to clients
- `prompts/`: reusable prompt templates
- `server/`: MCP wiring and stdio entrypoints

## Data Flow (triage_logs)

1. MCP tool receives inputs in `server/log_server.py`
2. Inputs are normalized in `tools/triage.py`
3. Time windows are resolved in `core/time_window.py`
4. Files are scanned and parsed asynchronously in `core/log_service.py`
5. Parsed `LogEntry` objects are returned to the tool and serialized

## Parsing Pipeline Details

- `core/scanning.py` samples the log to detect format and prefilter candidates
- `core/formats/` contains the parser implementations that normalize entries
- `core/log_service.py` applies time windows, severity filters, and substring
  filters before yielding entries

Async log IO is handled via `aiofiles` to keep the server responsive under
concurrent requests.

## Extension Points

- Add new parsers by implementing `LogParser` and inserting into the chain
- Add new resources or prompts in their respective registries
- Extend AI review by updating `core/ai_review.py` or adding new providers

## Why This Split

- Testability: pure logic is isolated in `core/`
- Clarity: MCP wiring stays thin and predictable
- Maintainability: modules have single, focused responsibilities
