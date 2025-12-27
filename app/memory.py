"""In-memory store for tracking pending clarifications."""

from __future__ import annotations

from typing import Optional, Tuple

_state = {
    "pending_question": None,
    "pending_clarification": None,
}


def set_pending(question: str, clarification: str) -> None:
    """Store the latest question and its clarification prompt."""
    _state["pending_question"] = question
    _state["pending_clarification"] = clarification


def get_pending() -> Tuple[Optional[str], Optional[str]]:
    """Return the pending question and clarification prompt."""
    return _state["pending_question"], _state["pending_clarification"]


def clear_pending() -> None:
    """Clear any pending clarification state."""
    _state["pending_question"] = None
    _state["pending_clarification"] = None
