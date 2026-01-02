"""Module entrypoint.

Allows:
    python -m mcp_log_triage_server
"""

from __future__ import annotations

from mcp_log_triage_server.server.log_server import main

if __name__ == "__main__":
    main()
