"""Deterministic normalization of user questions to canonical schema values."""

from __future__ import annotations

import re

COUNTRY_MAP = {
    "india": "IN",
    "united states": "US",
    "usa": "US",
    "us": "US",
    "united kingdom": "UK",
    "uk": "UK",
    "germany": "DE",
    "singapore": "SG",
}


def normalize_question(question: str) -> str:
    """Normalize human-friendly values to canonical schema codes."""
    normalized = question.lower()
    for human, code in COUNTRY_MAP.items():
        normalized = re.sub(rf"\b{re.escape(human)}\b", code, normalized, flags=re.IGNORECASE)
    return normalized
