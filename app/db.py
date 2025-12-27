"""Database connection utilities for the demo SQLite database."""

from __future__ import annotations

import sqlite3
import logging
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List
import re


FORBIDDEN_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
)


def get_demo_db_path() -> Path:
    """Return the absolute path to the demo SQLite database file."""
    return Path(__file__).resolve().parent.parent / "data" / "demo.db"


def get_connection() -> sqlite3.Connection:
    """Create a SQLite connection to the demo database with foreign keys on."""
    db_path = get_demo_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def execute_read_only_query(sql: str) -> Dict[str, Any]:
    """Execute a safe SELECT query and return columns, rows, and timing.

    Rejects any query containing write-related keywords or that does not start
    with SELECT/WITH. Rows are returned as dictionaries keyed by column name.
    """
    normalized_sql = sql.strip().rstrip(";")
    upper_sql = normalized_sql.upper()

    if not upper_sql.startswith(("SELECT", "WITH")):
        raise ValueError("Only SELECT queries are permitted.")

    for keyword in FORBIDDEN_KEYWORDS:
        pattern = rf"\b{keyword}\b"
        if re.search(pattern, upper_sql):
            raise ValueError("Write operations are not allowed in read-only mode.")

    with get_connection() as conn:
        start = perf_counter()
        try:
            cursor = conn.execute(normalized_sql)
            fetched_rows = cursor.fetchall()
        except sqlite3.Error as exc:
            logging.error("SQLite execution error: %s", exc)
            raise RuntimeError("SQLite execution error") from exc
        duration_ms = (perf_counter() - start) * 1000

        columns: List[str] = [desc[0] for desc in cursor.description] if cursor.description else []
        rows: List[Dict[str, Any]] = [dict(row) for row in fetched_rows]

    return {
        "columns": columns,
        "rows": rows,
        "execution_time_ms": round(duration_ms, 2),
    }
