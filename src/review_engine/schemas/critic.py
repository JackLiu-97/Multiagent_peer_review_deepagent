from __future__ import annotations

from pydantic import BaseModel, Field


class CriticResult(BaseModel):
    approved: bool = False
    failed_dimensions: list[str] = Field(default_factory=list)
    feedback_by_dimension: dict[str, str] = Field(default_factory=dict)
    cross_dimension_conflicts: list[str] = Field(default_factory=list)
    global_feedback: str = ""
