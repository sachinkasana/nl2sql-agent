"""Strong, schema-grounded prompt for NL -> SQL generation (SQLite native)."""

from __future__ import annotations

from .guardrails import get_schema_context

SQL_GENERATION_PROMPT = """You generate read-only SQL queries for SQLite.

Allowed schema (use only these tables and columns):
users(id, name, email, country, plan, created_at)
payments(id, user_id, amount, status, created_at)
events(id, user_id, name, created_at)
tickets(id, user_id, category, status, created_at)

Rules:
- ONLY use the tables and columns listed above. NEVER invent tables or columns.
- NEVER use SELECT *; list explicit columns.
- ONLY generate read-only SELECT queries.
- Use LIMIT 50 by default.
- Use created_at for time filtering with datetime('now', '<offset>').
- Output ONLY valid SQL (no explanations).
- If the question mentions a specific value (e.g., "from India", "in US", "country = Germany"), use a WHERE clause, NOT GROUP BY.
- Use GROUP BY ONLY when the question asks for comparisons or distributions (e.g., "by country", "per country", "grouped by").
- Country value mapping for users.country:
  - India -> 'IN'
  - United States / USA -> 'US'
  - United Kingdom / UK -> 'UK'
  - Germany -> 'DE'
  - Singapore -> 'SG'

Examples:

Example 1:
Question: Show users by country
SQL:
SELECT country, COUNT(*) AS user_count
FROM users
GROUP BY country
LIMIT 50;

Example 2:
Question: Show failed payments last 7 days
SQL:
SELECT COUNT(*) AS failed_payments
FROM payments
WHERE status = 'failed'
  AND created_at >= datetime('now', '-7 days')
LIMIT 50;

Example 3:
Question: Show open tickets by category
SQL:
SELECT category, COUNT(*) AS open_tickets
FROM tickets
WHERE status = 'open'
GROUP BY category
LIMIT 50;

Example 4:
Question: New users last 30 days
SQL:
SELECT COUNT(*) AS new_users
FROM users
WHERE created_at >= datetime('now', '-30 days')
LIMIT 50;

Example 5:
Question: Show users list from India
SQL:
SELECT *
FROM users
WHERE country = 'IN'
LIMIT 50;

Example 6:
Question: Show users from the US
SQL:
SELECT *
FROM users
WHERE country = 'US'
LIMIT 50;

Example 7:
Question: How many users are from India
SQL:
SELECT COUNT(*) AS user_count
FROM users
WHERE country = 'IN'
LIMIT 50;
"""


def build_sql_prompt(question: str) -> str:
    """Construct the full prompt by appending the user question at the end."""
    schema_context = get_schema_context()
    prompt = (
        SQL_GENERATION_PROMPT
        + "\n\nDatabase schema (for reference):\n"
        + schema_context
        + "\n\nQuestion: "
        + question
        + "\nSQL:"
    )
    return prompt
