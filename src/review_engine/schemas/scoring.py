from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BaseScoreResult(BaseModel):
    score_range: str = ""
    proposed_score: int = 0
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    major_penalties: list[str] = Field(default_factory=list)


class HistoryAnalysisResult(BaseModel):
    similar_case_count: int = 0
    score_distribution: dict[str, Any] = Field(default_factory=dict)
    common_problem_patterns: list[str] = Field(default_factory=list)
    recommended_adjustment: int = 0
    reason: str = ""


class FinalScoreResult(BaseModel):
    base_score: int = 0
    history_adjustment: int = 0
    final_score: int = 0
    final_grade_band: str = ""
    scoring_rationale: str = ""


class ScoringBundleResult(BaseModel):
    base_score_result: BaseScoreResult
    history_analysis_result: HistoryAnalysisResult
    final_score_result: FinalScoreResult
