"""Deterministic SQL builders for simple, single-table queries."""

from __future__ import annotations

from typing import Optional


def build_users_query(country: Optional[str], aggregate: bool) -> str:
    """Build a single-table users query without joins."""
    if aggregate:
        select_clause = "SELECT COUNT(*) AS user_count"
    else:
        select_clause = "SELECT *"

    sql = f"{select_clause}\nFROM users"
    if country:
        sql += f"\nWHERE country = '{country}'"

    sql += "\nLIMIT 50"
    return sql


def build_payments_query(status: Optional[str], since_days: Optional[int], aggregate: bool) -> str:
    """Build a single-table payments query without joins."""
    if aggregate:
        select_clause = "SELECT COUNT(*) AS failed_payments"
    else:
        select_clause = "SELECT *"

    sql_lines = [select_clause, "FROM payments"]

    where_clauses = []
    if status:
        where_clauses.append(f"status = '{status}'")
    if since_days:
        where_clauses.append(f"created_at >= datetime('now', '-{since_days} days')")

    if where_clauses:
        sql_lines.append("WHERE " + "\n  AND ".join(where_clauses))

    sql_lines.append("LIMIT 50")
    return "\n".join(sql_lines)
