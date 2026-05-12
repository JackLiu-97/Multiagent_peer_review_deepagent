from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    level: str = "normal"
    issue: str = ""
    evidence: str = ""
    suggestion: str = ""


class RawReviewPayload(BaseModel):
    overall_evaluation: str = ""
    strengths: list[str] = Field(default_factory=list)
    detailed_issue: list[ReviewIssue] = Field(default_factory=list)


class ReviewResult(BaseModel):
    dimension: str
    dimension_label: str
    round: int
    summary: str
    strengths: list[str] = Field(default_factory=list)
    issues: list[ReviewIssue] = Field(default_factory=list)
    confidence: float = 0.7
    needs_revision: bool = False


def normalize_review_payload(
    payload: dict[str, Any] | BaseModel,
    *,
    dimension: str,
    dimension_label: str,
    round_no: int,
) -> ReviewResult:
    data = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else dict(payload)
    issues = [ReviewIssue.model_validate(item) for item in (data.get("detailed_issue") or [])]
    needs_revision = any(item.level.lower() in {"critical", "major"} for item in issues)
    return ReviewResult(
        dimension=dimension,
        dimension_label=dimension_label,
        round=round_no,
        summary=str(data.get("overall_evaluation") or ""),
        strengths=[str(item).strip() for item in (data.get("strengths") or []) if str(item).strip()],
        issues=issues,
        confidence=0.8 if not needs_revision else 0.6,
        needs_revision=needs_revision,
    )
