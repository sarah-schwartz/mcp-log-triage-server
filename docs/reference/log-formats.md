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

## Fast Prefiltering

The scanner samples the first N lines to detect format and then uses a fast
byte-level scan to prefilter likely warning/error lines. This reduces the cost
of parsing large files while keeping the fallback path available when format
sniffing is inconclusive.
