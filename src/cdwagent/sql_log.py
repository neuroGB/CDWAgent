"""Append-only SQL audit log for executed queries.

Writes one line per executed read-only SQL statement to a file at
`$CDW_SQL_LOG` (default: `$TMPDIR/cdwagent_sql.log` on Unix, `~/cdwagent_sql.log` otherwise).

Format: `[ISO-UTC-timestamp] [PID] <single-line-SQL>`

Purpose:
  1. Operator audit trail — every SQL that hits the database is recorded
     independently of stdout/stderr piping (which BioRouter and other MCP
     clients route inconsistently).
  2. Eval / observability — a downstream test runner can read the file
     between case starts and ends to recover the exact SQL the agent ran.

Failure mode: writes are best-effort. If the log path is unwritable, the
function returns silently — a query must never fail because of an audit
side-effect.
"""
from __future__ import annotations

import datetime as _dt
import os
import tempfile
from pathlib import Path


def _default_log_path() -> Path:
    explicit = os.environ.get("CDW_SQL_LOG")
    if explicit:
        return Path(explicit)
    tmpdir = os.environ.get("TMPDIR") or tempfile.gettempdir()
    return Path(tmpdir) / "cdwagent_sql.log"


def log_sql(sql: str) -> None:
    """Append a single-line entry for `sql`. Best-effort, never raises."""
    try:
        path = _default_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        line = f"[{ts}] [{os.getpid()}] {' '.join(sql.split())}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        return  # never propagate — auditing must not break the query


def get_log_path() -> Path:
    """Expose the resolved log path (for runner / debugging)."""
    return _default_log_path()
