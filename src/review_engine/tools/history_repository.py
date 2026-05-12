from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from review_engine.tools.sql_readonly import ensure_readonly_sql


class HistoryRepository:
    def __init__(self, database_url: str = "") -> None:
        self.database_url = (database_url or "").strip()
        self.engine = create_engine(self.database_url) if self.database_url else None

    @property
    def available(self) -> bool:
        return self.engine is not None

    @property
    def database_name(self) -> str:
        if not self.database_url:
            return ""
        try:
            return make_url(self.database_url).database or ""
        except Exception:
            return ""

    def inspect_schema(self, table_pattern: str = "") -> dict[str, Any]:
        if not self.engine:
            return {"tables": []}

        inspector = inspect(self.engine)
        names = inspector.get_table_names()
        if table_pattern:
            normalized = table_pattern.replace("%", "").lower()
            names = [name for name in names if normalized in name.lower()]

        tables: list[dict[str, Any]] = []
        for name in names:
            columns = inspector.get_columns(name)
            tables.append(
                {
                    "table_name": name,
                    "columns": [{"name": col["name"], "type": str(col["type"])} for col in columns],
                }
            )
        return {"tables": tables}

    def query(self, sql: str) -> dict[str, Any]:
        if not self.engine:
            return {"columns": [], "rows": [], "row_count": 0}

        readonly_sql = ensure_readonly_sql(sql)
        with self.engine.begin() as conn:
            result = conn.execute(text(readonly_sql))
            rows = result.fetchmany(500)
            columns = list(result.keys())

        normalized_rows = [dict(zip(columns, row)) for row in rows]
        return {
            "columns": columns,
            "rows": normalized_rows,
            "row_count": len(normalized_rows),
        }

    def schema_hint(self) -> str:
        database = self.database_name
        if database == "whpy":
            return (
                "Current history scoring database: whpy.\n"
                "Recommended tables:\n"
                "1. t_reviews(review_id, paper_id, general_comment, suggestions, total_score, created_at)\n"
                "2. t_review_question(id, review_info_id, question, status)\n"
                "3. t_part_question(paper_id, part, review_question_id)\n"
                "4. t_papers(paper_id, title, abstract_text, major_code, degree_type, keywords, publish_year)\n"
                "5. t_review_scores(review_id, dim_1_score ... dim_5_score)\n"
                "Suggested query strategy:\n"
                "- Prefer t_reviews.total_score for score ranges and distribution.\n"
                "- Prefer t_review_question.question joined with t_part_question for similar problem patterns.\n"
                "- For abstract use part=1, for methods use part=2, for references use part=3.\n"
                "- For introduction use part=4 and optionally add keyword filters related to background or innovation.\n"
                "- Only readonly SELECT / WITH queries are allowed.\n"
            )
        return (
            f"Current history database: {database or 'unknown'}.\n"
            "Inspect schema first with db_schema_inspect, then decide the query path."
        )
