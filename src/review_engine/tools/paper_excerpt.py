from __future__ import annotations

from pydantic import BaseModel, Field

from review_engine.schemas import ToolSpec


class PaperExcerptInput(BaseModel):
    start_line: int = Field(..., ge=1, description="起始行号，从 1 开始。")
    end_line: int = Field(..., ge=1, description="结束行号，包含该行。")


def create_paper_excerpt_tool(full_markdown: str) -> ToolSpec:
    lines = full_markdown.splitlines()

    def handler(start_line: int, end_line: int) -> dict:
        start = max(1, start_line)
        end = max(start, end_line)
        snippet = lines[start - 1 : end]
        return {
            "start_line": start,
            "end_line": end,
            "text": "\n".join(snippet),
        }

    return ToolSpec(
        name="paper_excerpt_lookup",
        description="按行号返回论文全文 Markdown 的连续片段。",
        input_model=PaperExcerptInput,
        handler=handler,
    )
