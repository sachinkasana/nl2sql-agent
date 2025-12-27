"""SQL safety, schema grounding, and validation utilities."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

# Allowed schema for grounding and validation
ALLOWED_SCHEMA: Dict[str, List[str]] = {
    "users": ["id", "name", "email", "country", "plan", "created_at"],
    "payments": ["id", "user_id", "amount", "status", "created_at"],
    "events": ["id", "user_id", "name", "created_at"],
    "tickets": ["id", "user_id", "category", "status", "created_at"],
}


def get_schema_context() -> str:
    """Return a human-readable schema outline for prompts."""
    lines = []
    for table, columns in ALLOWED_SCHEMA.items():
        cols = ", ".join(columns)
        lines.append(f"{table}({cols})")
    return "\n".join(lines)


FORBIDDEN_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "attach",
    "pragma",
    "intersect",
)


def _uses_only_allowed_tables(sql_lower: str) -> bool:
    """Check that referenced tables are within the allowed schema."""
    tables = set(re.findall(r"\bfrom\s+([a-zA-Z_][\w]*)", sql_lower))
    tables.update(re.findall(r"\bjoin\s+([a-zA-Z_][\w]*)", sql_lower))
    return all(table in ALLOWED_SCHEMA for table in tables) if tables else True


def _has_self_join(sql_lower: str) -> bool:
    """Detect self-joins on the same table."""
    from_tables = re.findall(r"\bfrom\s+([a-zA-Z_][\w]*)", sql_lower)
    join_tables = re.findall(r"\bjoin\s+([a-zA-Z_][\w]*)", sql_lower)
    return any(jt in from_tables for jt in join_tables)


def _references_large_tables_without_time_filter(sql_lower: str) -> bool:
    """Determine if large tables are referenced without created_at constraints."""
    references_large_table = any(name in sql_lower for name in ("payments", "events"))
    has_time_filter = "created_at" in sql_lower
    return references_large_table and not has_time_filter


def validate_sql(sql: str) -> Dict[str, Optional[str]]:
    """Validate SQL for safety and schema compliance.

    Returns a unified contract:
    {
        "status": "success" | "blocked" | "clarification_needed",
        "sql": "possibly modified sql",
        "warnings": [],
        "reason": str | None,
        "question": str | None
    }
    """
    normalized = sql.strip()
    sql_lower = normalized.lower()

    # Block dangerous keywords with word-boundary matching to avoid false positives
    forbidden_hit = None
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql_lower, flags=re.IGNORECASE):
            forbidden_hit = keyword
            break

    if forbidden_hit:
        return {
            "status": "blocked",
            "sql": None,
            "warnings": [],
            "reason": f"Query contains forbidden keyword: {forbidden_hit}.",
            "question": None,
        }

    # Block multiple statements
    if normalized.count(";") > 1:
        return {
            "status": "blocked",
            "sql": None,
            "warnings": [],
            "reason": "Multiple SQL statements are not allowed.",
            "question": None,
        }

    # Enforce allowed tables only
    if not _uses_only_allowed_tables(sql_lower):
        return {
            "status": "blocked",
            "sql": None,
            "warnings": [],
            "reason": "Query references tables outside the allowed schema.",
            "question": None,
        }

    # Block self-joins
    if _has_self_join(sql_lower):
        return {
            "status": "blocked",
            "sql": None,
            "warnings": [],
            "reason": "Self-joins are not allowed for analytics queries.",
            "question": None,
        }

    # Block SELECT *
    if re.search(r"select\s+\*", sql_lower):
        return {
            "status": "blocked",
            "sql": None,
            "warnings": [],
            "reason": "SELECT * is not allowed; specify explicit columns.",
            "question": None,
        }

    # Enforce time window for large tables
    if _references_large_tables_without_time_filter(sql_lower):
        return {
            "status": "clarification_needed",
            "sql": None,
            "warnings": [],
            "reason": None,
            "question": "Which time range do you want? (last 7 days / last 30 days / custom)",
        }

    warnings: List[str] = []
    if "limit" not in sql_lower:
        normalized = f"{normalized.rstrip(';')} LIMIT 50"
        warnings.append("LIMIT 50 was automatically applied for safety")

    return {
        "status": "success",
        "sql": normalized,
        "warnings": warnings,
        "reason": None,
        "question": None,
    }
