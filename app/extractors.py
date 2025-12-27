"""Deterministic extractors for canonical values from normalized questions."""

from __future__ import annotations

import re
from typing import Optional


def extract_country(question: str) -> Optional[str]:
    """Extract the first canonical country code from a normalized question."""
    match = re.search(r"\b(in|us|uk|de|sg)\b", question.lower())
    if match:
        return match.group(1).upper()
    return None
