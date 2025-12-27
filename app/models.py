"""Pydantic models for request and response payloads."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Incoming NL -> SQL question payload."""

    question: str = Field(..., description="Natural language question to answer")


class AskResponse(BaseModel):
    """Structured response returned by the agent."""

    answer: str = Field(..., description="Human-friendly answer to the question")
    sql: Optional[str] = Field(
        default=None, description="Generated SQL statement, if available"
    )
    rows: Optional[List[Any]] = Field(
        default_factory=list, description="Row-level results when applicable"
    )
    explanation: Optional[str] = Field(
        default=None, description="Explanation of how the answer was derived"
    )
    confidence: float = Field(..., description="Model confidence between 0 and 1")
    warnings: List[str] = Field(
        default_factory=list, description="Any safety or validation warnings"
    )
