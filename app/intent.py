"""Simple rule-based intent detection for NL -> SQL questions."""

from __future__ import annotations

import re
from typing import Dict


def detect_intent(question: str) -> Dict[str, bool]:
    """Detect basic intents using keyword-based heuristics."""
    q = question.lower()

    is_filter = bool(re.search(r"\b(from|in|where)\b", q))
    is_group_by = bool(re.search(r"\b(by|per|grouped by)\b", q))
    is_aggregate = bool(re.search(r"\b(count|how many|total|sum)\b", q))
    has_time_range = bool(re.search(r"\b(last|past|\d+\s*days|\d+\s*weeks|\d+\s*months)\b", q))

    return {
        "is_filter": is_filter,
        "is_group_by": is_group_by,
        "is_aggregate": is_aggregate,
        "has_time_range": has_time_range,
    }
