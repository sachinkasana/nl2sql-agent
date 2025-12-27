"""Agent orchestration with NL->SQL generation, guardrails, and safe execution."""

from __future__ import annotations

import re
from typing import List

from transformers import pipeline

from . import db
from .guardrails import validate_sql
from .intent import detect_intent
from .normalize import normalize_question
from .memory import clear_pending, get_pending, set_pending
from .models import AskResponse
from .prompts import build_sql_prompt
from .sql_builder import build_users_query, build_payments_query
from .extractors import extract_country

#MODEL_NAME = "tscholak/finetuned-t5-small-sqlite"
MODEL_NAME = "google/flan-t5-base"  # or t5-small variant

_generator = None


def load_model() -> None:
    """Load the text2text-generation pipeline once at startup (CPU only)."""
    global _generator
    if _generator is None:
        _generator = pipeline(
            "text2text-generation",
            model=MODEL_NAME,
            tokenizer=MODEL_NAME,
            device=-1,  # CPU
        )


def _clean_sql(generated_text: str) -> str:
    """Strip code fences and explanations, keeping only SQL."""
    text = generated_text.strip()
    text = re.sub(r"```sql|```", "", text, flags=re.IGNORECASE).strip()
    # Attempt to extract the first SQL statement ending with semicolon
    match = re.search(r"(select[\s\S]*?;)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback to first line if no semicolon found
    lines = text.splitlines()
    candidate = lines[0] if lines else text
    return candidate.strip()


def is_followup_answer(text: str) -> bool:
    """Detect short follow-up answers to clarification prompts."""
    t = text.strip().lower()
    return t in {
        "list",
        "show list",
        "just the list",
        "count",
        "just the count",
        "total",
        "last 7 days",
        "last 30 days",
    }


def needs_clarification(intent: dict, question: str) -> str | None:
    """Return a clarification question if the intent is ambiguous."""
    q = question.lower()
    # Rule 1: payments/events without time range
    if (("payment" in q) or ("event" in q)) and not intent.get("has_time_range", False):
        return "Which time range should I use? (last 7 days / last 30 days / custom)"

    # Rule 2: ambiguous country mention
    if "america" in q:
        return "Did you mean United States (US)?"

    # Rule 3: filter intent without aggregate intent
    if intent.get("is_filter") and not intent.get("is_aggregate"):
        list_markers = (" list", "show list", "just the list")
        count_markers = ("count", "how many", "total", "just the count")
        if any(marker in q for marker in list_markers):
            return None
        if any(marker in q for marker in count_markers):
            return None
        return "Do you want the list or just the count?"

    return None


def _resolve_followup(pending_question: str, follow_up: str) -> str | None:
    """Combine a pending question with a short follow-up reply."""
    base = pending_question.strip()
    follow = follow_up.strip()
    low_follow = follow.lower()
    base_no_show = re.sub(r"(?i)^show\s+", "", base).strip()

    aggregate_keywords = ("count", "how many", "total", "sum")
    list_keywords = ("list", "show")
    time_keywords = ("days", "weeks", "months", "last", "past")

    if any(k in low_follow for k in time_keywords):
        return f"{base} {follow}"

    if any(k in low_follow for k in aggregate_keywords):
        return f"How many {base_no_show}"

    if any(k in low_follow for k in list_keywords):
        return f"Show {base_no_show}"

    return None


def run_agent(question: str) -> AskResponse:
    """Process a user question end-to-end with model, guardrails, and execution."""
    pending_question, _ = get_pending()
    combined_question = question

    # Consume short follow-up answers before any other processing.
    if pending_question and is_followup_answer(question):
        combined_question = f"{pending_question} {question}"
        clear_pending()
    elif pending_question:
        resolved = _resolve_followup(pending_question, question)
        if resolved:
            combined_question = resolved
            clear_pending()
        else:
            clear_pending()

    normalized_question = normalize_question(combined_question)

    intent = detect_intent(normalized_question)
    lower_q = normalized_question.lower()

    # Explicit user intent overrides inferred aggregation (count wins if both appear).
    count_markers = ("count", "how many", "total")
    list_markers = (" list", "show ", "details")
    if any(marker in lower_q for marker in count_markers):
        intent["is_aggregate"] = True
    elif any(marker in lower_q for marker in list_markers):
        intent["is_aggregate"] = False

    clar_question = needs_clarification(intent, normalized_question)
    if clar_question:
        set_pending(combined_question, clar_question)
        return AskResponse(
            answer="I need more information to answer this.",
            explanation=clar_question,
            confidence=0.4,
            warnings=[],
        )

    lower_q = normalized_question.lower()
    is_simple_query = is_simple_query = (
    intent.get("is_filter")
    or intent.get("is_aggregate")
    or (
        "payment" in lower_q
        and intent.get("has_time_range")
    )
)
    has_group_by = intent.get("is_group_by")
    has_join_keywords = any(k in lower_q for k in (" join ", "join "))

    # Deterministic routing for simple, single-table payments queries (filter or aggregate, no group/join).
    is_payments_query = "payment" in lower_q
    if (
        is_payments_query
        and is_simple_query
        and not has_group_by
        and not has_join_keywords
    ):
        status = "failed" if "failed" in lower_q else None
        since_days = 7 if "7 days" in lower_q or "last 7 days" in lower_q else None
        if "30 days" in lower_q or "last 30 days" in lower_q:
            since_days = 30
        aggregate = intent.get("is_aggregate", False)
        deterministic_sql = build_payments_query(
            status=status, since_days=since_days, aggregate=aggregate
        )
        try:
            result = db.execute_read_only_query(deterministic_sql)
            rows = result.get("rows", [])
            columns = result.get("columns", [])
            explanation = "Query executed via deterministic routing."
            if columns and rows:
                explanation = f"Returned {len(rows)} rows with columns: {', '.join(columns)}."
            return AskResponse(
                answer="Here are the results of your query.",
                sql=deterministic_sql,
                rows=rows,
                explanation=explanation,
                confidence=0.7,
                warnings=[],
            )
        except Exception:
            return AskResponse(
                answer="",
                sql=deterministic_sql,
                rows=[],
                explanation="Query execution failed.",
                confidence=0.4,
                warnings=["Deterministic path execution failed."],
            )

    # Deterministic routing for simple, single-table users queries (filter or aggregate, no group/join).
    is_users_query = "users" in lower_q
    references_other_tables = any(name in lower_q for name in ("payment", "event", "ticket"))

    if (
        is_users_query
        and is_simple_query
        and not has_group_by
        and not references_other_tables
        and not has_join_keywords
    ):
        country_code = extract_country(normalized_question)
        aggregate = intent.get("is_aggregate", False)
        deterministic_sql = build_users_query(country=country_code, aggregate=aggregate)
        try:
            result = db.execute_read_only_query(deterministic_sql)
            rows = result.get("rows", [])
            columns = result.get("columns", [])
            explanation = "Query executed via deterministic routing."
            if columns and rows:
                explanation = f"Returned {len(rows)} rows with columns: {', '.join(columns)}."
            return AskResponse(
                answer="Here are the results of your query.",
                sql=deterministic_sql,
                rows=rows,
                explanation=explanation,
                confidence=0.7,
                warnings=[],
            )
        except Exception:
            return AskResponse(
                answer="",
                sql=deterministic_sql,
                rows=[],
                explanation="Query execution failed.",
                confidence=0.4,
                warnings=["Deterministic path execution failed."],
            )

    load_model()
    intent_hint = (
        f" Intent hints: filter={intent['is_filter']}, "
        f"group_by={intent['is_group_by']}, aggregate={intent['is_aggregate']}, "
        f"has_time_range={intent['has_time_range']}."
    )
    prompt = build_sql_prompt(normalized_question + intent_hint)

    try:
        generation = _generator(prompt, max_length=256, num_return_sequences=1)
        raw_sql = generation[0]["generated_text"]
    except Exception:
        return AskResponse(
            answer="",
            sql="",
            rows=[],
            explanation="Failed to generate SQL from the model.",
            confidence=0.0,
            warnings=["Model generation failed; please try rephrasing your question."],
        )

    proposed_sql = _clean_sql(raw_sql)
    validation = validate_sql(proposed_sql)
    status = validation["status"]
    safe_sql = validation.get("sql")
    warnings: List[str] = validation.get("warnings", [])

    if status == "blocked":
        reason = validation.get("reason") or "Query was blocked for safety reasons."
        warnings.append(reason)
        return AskResponse(
            answer="",
            sql="",
            rows=[],
            explanation="Query was blocked for safety reasons.",
            confidence=0.0,
            warnings=warnings,
        )

    if status == "clarification_needed":
        return AskResponse(
            answer="",
            explanation=validation.get("question")
            or "I need a time range to run this query safely.",
            confidence=0.4,
            warnings=warnings,
        )

    # At this point, validation succeeded; execute read-only query safely.
    executable_sql = safe_sql or proposed_sql
    try:
        result = db.execute_read_only_query(executable_sql)
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        explanation = "Query executed safely with guardrails applied."
        if columns and rows:
            explanation = f"Returned {len(rows)} rows with columns: {', '.join(columns)}."
        return AskResponse(
            answer="Here are the results of your query.",
            sql=executable_sql,
            rows=rows,
            explanation=explanation,
            confidence=0.7,
            warnings=warnings,
        )
    except Exception:
        warnings.append("Query failed to execute. Please adjust your request.")
        return AskResponse(
            answer="",
            sql=executable_sql,
            rows=[],
            explanation="Query execution failed.",
            confidence=0.4,
            warnings=warnings,
        )
