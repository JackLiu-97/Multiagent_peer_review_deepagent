from __future__ import annotations

from review_engine.core.dimensions import DIMENSION_ORDER, get_dimension_config


def render_markdown_report(state: dict) -> str:
    lines: list[str] = []
    final_score = state.get("final_score_result") or {}
    base_score = state.get("base_score_result") or {}
    critic_result = state.get("critic_result") or {}
    reviews = state.get("review_results") or {}
    history_result = state.get("history_analysis_result") or {}

    lines.append("# 学位论文评审意见书")
    lines.append("")
    lines.append("## 论文信息")
    lines.append(f"- 论文编号: {state.get('paper_id', '')}")
    lines.append(f"- 论文题目: {state.get('thesis_title', '')}")
    lines.append(f"- 使用轮次: {state.get('current_round', 1)}")
    lines.append("")
    lines.append("## 评分结果")
    lines.append(f"- 基础分: {base_score.get('proposed_score', 0)}")
    lines.append(f"- 历史校准: {history_result.get('recommended_adjustment', 0)}")
    lines.append(f"- 最终建议分数: {final_score.get('final_score', 0)}")
    lines.append(f"- 建议区间: {final_score.get('final_grade_band', '')}")
    lines.append(f"- 评分说明: {final_score.get('scoring_rationale', '')}")
    lines.append("")
    lines.append("## Critic 审核")
    lines.append(f"- 是否通过: {'是' if critic_result.get('approved') else '否'}")
    if critic_result.get("global_feedback"):
        lines.append(f"- 总体反馈: {critic_result.get('global_feedback')}")
    conflicts = critic_result.get("cross_dimension_conflicts") or []
    if conflicts:
        lines.append("- 跨维度冲突:")
        for item in conflicts:
            lines.append(f"  - {item}")
    lines.append("")
    lines.append("## 分维度评审")

    for dimension_key in DIMENSION_ORDER:
        config = get_dimension_config(dimension_key)
        result = reviews.get(dimension_key) or {}
        lines.append("")
        lines.append(f"### {config.label}")
        lines.append(f"- 总评: {result.get('summary', '')}")

        strengths = result.get("strengths") or []
        if strengths:
            lines.append("- 优点:")
            for item in strengths:
                lines.append(f"  - {item}")

        issues = result.get("issues") or []
        if issues:
            lines.append("- 主要问题:")
            for issue in issues:
                lines.append(f"  - [{issue.get('level', 'normal')}] {issue.get('issue', '')}")
                if issue.get("evidence"):
                    lines.append(f"    - 证据: {issue.get('evidence')}")
                if issue.get("suggestion"):
                    lines.append(f"    - 建议: {issue.get('suggestion')}")

    lines.append("")
    lines.append("## 历史校准")
    lines.append(f"- 相似样本数: {history_result.get('similar_case_count', 0)}")
    if history_result.get("score_distribution"):
        lines.append(f"- 分数分布: {history_result.get('score_distribution')}")
    if history_result.get("reason"):
        lines.append(f"- 说明: {history_result.get('reason')}")
    patterns = history_result.get("common_problem_patterns") or []
    if patterns:
        lines.append("- 共性问题:")
        for item in patterns:
            lines.append(f"  - {item}")

    return "\n".join(lines).strip() + "\n"
