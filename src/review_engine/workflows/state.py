from __future__ import annotations

from typing import Annotated, Any, TypedDict


def merge_dicts(existing: dict[str, Any] | None, new: dict[str, Any] | None) -> dict[str, Any]:
    result = dict(existing or {})
    if new:
        result.update(new)
    return result


def merge_history(
    existing: dict[str, list[dict[str, Any]]] | None,
    new: dict[str, list[dict[str, Any]]] | None,
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {
        key: list(value) for key, value in (existing or {}).items()
    }
    for key, items in (new or {}).items():
        result.setdefault(key, [])
        result[key].extend(items)
    return result


class ReviewWorkflowState(TypedDict, total=False):
    paper_id: str
    thesis_title: str
    full_markdown: str
    input_path: str
    output_dir: str

    dimension_order: list[str]
    pending_dimensions: list[str]
    current_round: int
    max_rounds: int

    review_results: Annotated[dict[str, dict[str, Any]], merge_dicts]
    review_history: Annotated[dict[str, list[dict[str, Any]]], merge_history]
    critic_result: dict[str, Any]

    base_score_result: dict[str, Any]
    history_analysis_result: dict[str, Any]
    final_score_result: dict[str, Any]

    formatted_report_markdown: str
    formatted_report_html: str
    final_result: dict[str, Any]
