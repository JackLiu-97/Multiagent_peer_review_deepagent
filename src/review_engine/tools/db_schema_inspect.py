from __future__ import annotations

from pydantic import BaseModel, Field

from review_engine.schemas import ToolSpec


class DBSchemaInspectInput(BaseModel):
    table_pattern: str = Field(default="", description="可选的表名过滤关键字。")


def create_db_schema_inspect_tool(history_repository) -> ToolSpec:
    def handler(table_pattern: str = "") -> dict:
        return history_repository.inspect_schema(table_pattern=table_pattern)

    return ToolSpec(
        name="db_schema_inspect",
        description="查看历史评分数据库的表结构与字段信息。",
        input_model=DBSchemaInspectInput,
        handler=handler,
    )
