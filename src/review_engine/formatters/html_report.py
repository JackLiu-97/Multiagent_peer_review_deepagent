from __future__ import annotations

import html
from datetime import date

from review_engine.core.dimensions import DIMENSION_ORDER


SECTION_TAG_MAP = {
    "abstract": "摘要",
    "introduction": "绪论",
    "methods": "相关工作与方法",
    "references": "参考文献",
}
SEVERITY_ORDER = {"critical": 0, "major": 1, "normal": 2, "low": 3}


def _esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _severity_key(level: object) -> str:
    normalized = str(level or "normal").strip().lower()
    if normalized in SEVERITY_ORDER:
        return normalized
    return "normal"


def _dimension_label(dimension_key: str) -> str:
    return SECTION_TAG_MAP.get(dimension_key, dimension_key)


def _collect_strengths_and_issues(state: dict) -> tuple[list[str], list[dict], list[dict]]:
    reviews = state.get("review_results") or {}
    strengths: list[str] = []
    seen: set[str] = set()
    general_issues: list[dict] = []
    reference_issues: list[dict] = []

    for dimension_key in DIMENSION_ORDER:
        review = reviews.get(dimension_key) or {}
        for item in review.get("strengths") or []:
            text = str(item).strip()
            if text and text not in seen:
                strengths.append(text)
                seen.add(text)

        for raw_issue in review.get("issues") or []:
            issue = raw_issue if isinstance(raw_issue, dict) else {}
            item = {
                "level": _severity_key(issue.get("level")),
                "issue": str(issue.get("issue") or "").strip(),
                "evidence": str(issue.get("evidence") or "").strip(),
                "suggestion": str(issue.get("suggestion") or "").strip(),
                "tag": _dimension_label(dimension_key),
            }
            if not item["issue"]:
                continue
            if dimension_key == "references":
                reference_issues.append(item)
            else:
                general_issues.append(item)

    general_issues.sort(key=lambda item: SEVERITY_ORDER[item["level"]])
    reference_issues.sort(key=lambda item: SEVERITY_ORDER[item["level"]])
    return strengths, general_issues, reference_issues


def _render_issue_cards(issues: list[dict], empty_message: str) -> str:
    if not issues:
        return f'<div class="issue-card empty">{_esc(empty_message)}</div>'

    cards: list[str] = []
    for index, issue in enumerate(issues, start=1):
        cards.append(
            '<div class="issue-card">'
            '<div class="issue-head">'
            f'<span class="issue-num">{index}</span>'
            f'<span class="severity {_esc(issue["level"])}">{_esc(issue["level"].upper())}</span>'
            f'<span class="issue-title">{_esc(issue["issue"])}</span>'
            f'<span class="issue-tag">{_esc(issue["tag"])}</span>'
            "</div>"
            '<div class="issue-body">'
            f'<p>{_esc(issue["issue"])}</p>'
            f'<div class="evidence"><strong>原文证据：</strong>{_esc(issue["evidence"] or "未提供")}</div>'
            f'<div class="suggestion"><strong>修改建议：</strong>{_esc(issue["suggestion"] or "未提供")}</div>'
            "</div>"
            "</div>"
        )
    return "".join(cards)


def render_html_report(markdown_text: str, state: dict) -> str:
    del markdown_text
    strengths, general_issues, reference_issues = _collect_strengths_and_issues(state)
    final_score = state.get("final_score_result") or {}
    base_score = state.get("base_score_result") or {}
    history = state.get("history_analysis_result") or {}
    critic = state.get("critic_result") or {}

    strengths_html = "".join(f"<li>{_esc(item)}</li>" for item in strengths) or "<li>暂无。</li>"
    general_html = _render_issue_cards(general_issues, "未发现需要单独列出的共性问题。")
    reference_html = _render_issue_cards(reference_issues, "未发现需要单独列出的参考文献问题。")
    dimension_scores = base_score.get("dimension_scores") or {}
    dimension_score_html = "".join(
        f"<li><span>{_esc(_dimension_label(key))}</span><strong>{_esc(value)}</strong></li>"
        for key, value in dimension_scores.items()
    ) or "<li><span>暂无</span><strong>-</strong></li>"
    patterns_html = "".join(
        f"<li><span>{_esc(item)}</span></li>"
        for item in (history.get("common_problem_patterns") or [])
    ) or "<li><span>暂无历史共性模式</span></li>"

    overall_comment = " ".join(
        part
        for part in [
            f"最终建议得分为 {final_score.get('final_score', 0)} 分。",
            "当前评审结果已通过 critic 审核。" if critic.get("approved") else "当前评审结果未完全通过 critic 审核。",
            str(critic.get("global_feedback") or "").strip(),
            str(history.get("reason") or "").strip(),
        ]
        if part
    ).strip()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(state.get("thesis_title") or "学位论文评审意见书")}</title>
  <style>
    :root {{
      --primary: #1a3a5c;
      --accent: #2f6ea5;
      --border: #d9e2ec;
      --bg: #f5f7fa;
      --card: #ffffff;
      --text: #2c3e50;
      --muted: #718096;
      --critical: #c0392b;
      --major: #d35400;
      --normal: #b9770e;
      --low: #7f8c8d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Songti SC", "SimSun", serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.8;
      padding: 24px;
    }}
    .page {{
      max-width: 960px;
      margin: 0 auto;
      background: var(--card);
      padding: 48px 56px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    }}
    .header {{
      text-align: center;
      border-bottom: 3px double var(--primary);
      padding-bottom: 18px;
      margin-bottom: 28px;
    }}
    .header h1 {{
      margin: 0 0 16px;
      color: var(--primary);
      letter-spacing: 4px;
      font-size: 28px;
    }}
    .meta {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    .meta td {{
      padding: 6px 8px;
    }}
    .meta td:first-child {{
      width: 120px;
      color: var(--muted);
      text-align: right;
    }}
    .section {{
      margin-top: 28px;
    }}
    .section h2 {{
      margin: 0 0 14px;
      font-size: 18px;
      color: var(--primary);
      border-bottom: 1px solid var(--border);
      padding-bottom: 8px;
    }}
    .summary {{
      border-left: 4px solid var(--accent);
      background: #f7fbff;
      padding: 16px 18px;
      border-radius: 4px;
    }}
    .score-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}
    .score-item {{
      background: #fbfdff;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 14px;
      text-align: center;
    }}
    .score-item strong {{
      display: block;
      margin-top: 6px;
      font-size: 24px;
      color: var(--primary);
    }}
    .score-lists {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-top: 18px;
    }}
    .score-lists ul, .pros ul {{
      margin: 0;
      padding-left: 20px;
    }}
    .issue-card {{
      border: 1px solid var(--border);
      border-radius: 6px;
      margin-bottom: 14px;
      overflow: hidden;
      background: #fff;
    }}
    .issue-card.empty {{
      padding: 16px;
      color: var(--muted);
    }}
    .issue-head {{
      display: flex;
      gap: 10px;
      align-items: center;
      background: #f8fafc;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
    }}
    .issue-num {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background: var(--primary);
      color: white;
      font-size: 13px;
    }}
    .severity {{
      padding: 2px 8px;
      border-radius: 3px;
      color: white;
      font-size: 12px;
    }}
    .severity.critical {{ background: var(--critical); }}
    .severity.major {{ background: var(--major); }}
    .severity.normal {{ background: var(--normal); color: #fff; }}
    .severity.low {{ background: var(--low); }}
    .issue-title {{ flex: 1; font-weight: 700; }}
    .issue-tag {{
      font-size: 12px;
      color: var(--muted);
      background: #edf2f7;
      padding: 2px 8px;
      border-radius: 999px;
    }}
    .issue-body {{
      padding: 14px 16px;
    }}
    .evidence, .suggestion {{
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px dashed var(--border);
      font-size: 14px;
    }}
    .footer {{
      margin-top: 40px;
      padding-top: 16px;
      border-top: 1px solid var(--border);
      text-align: center;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 768px) {{
      body {{ padding: 12px; }}
      .page {{ padding: 24px 18px; }}
      .score-grid, .score-lists {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <h1>学位论文评审意见书</h1>
      <table class="meta">
        <tr><td>论文编号</td><td>{_esc(state.get("paper_id"))}</td></tr>
        <tr><td>论文题目</td><td>{_esc(state.get("thesis_title"))}</td></tr>
        <tr><td>评审日期</td><td>{_esc(date.today().strftime("%Y-%m-%d"))}</td></tr>
        <tr><td>评审方式</td><td>LangGraph + Deep Agents 固定维度评审</td></tr>
      </table>
    </div>

    <div class="section">
      <h2>总体评价</h2>
      <div class="summary">{_esc(overall_comment or "暂无总体评价。")}</div>
    </div>

    <div class="section">
      <h2>评分结果</h2>
      <div class="score-grid">
        <div class="score-item"><span>基础分</span><strong>{_esc(base_score.get("proposed_score", 0))}</strong></div>
        <div class="score-item"><span>历史校准</span><strong>{_esc(history.get("recommended_adjustment", 0))}</strong></div>
        <div class="score-item"><span>最终分</span><strong>{_esc(final_score.get("final_score", 0))}</strong></div>
        <div class="score-item"><span>相似样本</span><strong>{_esc(history.get("similar_case_count", 0))}</strong></div>
      </div>
      <p><strong>建议区间：</strong>{_esc(final_score.get("final_grade_band") or "暂无")}</p>
      <p><strong>评分说明：</strong>{_esc(final_score.get("scoring_rationale") or "暂无")}</p>
      <div class="score-lists">
        <div>
          <h3>分维度得分</h3>
          <ul>{dimension_score_html}</ul>
        </div>
        <div>
          <h3>历史共性问题</h3>
          <ul>{patterns_html}</ul>
        </div>
      </div>
    </div>

    <div class="section pros">
      <h2>主要优点</h2>
      <ul>{strengths_html}</ul>
    </div>

    <div class="section">
      <h2>评审详细意见</h2>
      {general_html}
    </div>

    <div class="section">
      <h2>参考文献规范意见</h2>
      {reference_html}
    </div>

    <div class="footer">Multi-Agent Peer Review System | Powered by LangGraph + Deep Agents</div>
  </div>
</body>
</html>
"""
