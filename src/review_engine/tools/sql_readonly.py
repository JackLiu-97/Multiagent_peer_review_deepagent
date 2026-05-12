from __future__ import annotations

import re

from pydantic import BaseModel, Field

from review_engine.schemas import ToolSpec


READONLY_PREFIX = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|MERGE)\b",
    re.IGNORECASE,
)


def ensure_readonly_sql(sql: str) -> str:
    normalized = (sql or "").strip().rstrip(";")
    if not READONLY_PREFIX.match(normalized):
        raise ValueError("Only SELECT / WITH readonly SQL is allowed.")
    if FORBIDDEN_SQL.search(normalized):
        raise ValueError("Write or DDL SQL is forbidden.")
    return normalized


class SQLReadonlyInput(BaseModel):
    sql: str = Field(..., description="只读 SQL，仅允许 SELECT 或 WITH。")


def create_sql_readonly_tool(history_repository) -> ToolSpec:
    def handler(sql: str) -> dict:
        return history_repository.query(sql)

    return ToolSpec(
        name="sql_readonly_query",
        description="对历史数据库执行只读 SQL 查询，仅允许 SELECT 或 WITH。",
        input_model=SQLReadonlyInput,
        handler=handler,
    )
