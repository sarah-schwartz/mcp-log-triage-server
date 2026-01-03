---
title: Log Formats
description: Supported log formats and parsing behavior.
---

The parser chain is ordered and stops on the first match:

1. Syslog (RFC5424 or RFC3164)
2. Access logs (Common/Combined)
3. Bracketed timestamps (`<timestamp> [LEVEL] <message>`)
4. JSON lines (`{"timestamp": "...", "level": "...", "message": "..."}`)
5. Loose level keywords (fallback)

## Syslog

RFC5424 and RFC3164 are supported. Severity is derived from the PRI value and
mapped to the normalized levels (CRITICAL, ERROR, WARNING, INFO, DEBUG).

Example:

```
<34>1 2025-12-30T08:12:04Z host app 1234 - - upstream timeout
```

## Access Logs

Common/Combined formats are supported. HTTP status is mapped to severity:

- 5xx -> ERROR
- 4xx -> WARNING
- 2xx/3xx -> INFO

Example:

```
127.0.0.1 - - [30/Dec/2025:08:12:04 +0000] "GET /items HTTP/1.1" 500 123
```

## Bracketed Timestamps

Format: `<timestamp> [LEVEL] <message>`. Supported timestamp formats include
`%Y-%m-%d %H:%M:%S`, `%Y/%m/%d %H:%M:%S`, and `%d-%m-%Y %H:%M:%S`.

Example:

```
2025-12-30 08:12:04 [ERROR] upstream timeout
```

## JSON Lines

Each line is a JSON object. Common keys are recognized:

- Timestamp: `timestamp`, `time`, `ts`
- Level: `level`, `severity`, `lvl`, `log_level`
- Message: `message`, `msg`, `error`, `detail`

Example:

```
{"timestamp":"2025-12-30T08:12:04Z","level":"error","message":"timeout"}
```

## Loose Level Keywords

If no structured format matches, the parser scans for severity keywords
anywhere in the line and returns a best-effort `LogEntry`.

## Fast Prefiltering

The scanner samples the first N lines to detect format and then uses a fast
byte-level scan to prefilter likely warning/error lines. This reduces the cost
of parsing large files while keeping the fallback path available when format
sniffing is inconclusive.
