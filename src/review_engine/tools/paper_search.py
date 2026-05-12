from __future__ import annotations

from pydantic import BaseModel, Field

from review_engine.schemas import ToolSpec


class PaperKeywordSearchInput(BaseModel):
    keyword: str = Field(..., description="需要在论文全文中检索的关键词。")
    max_hits: int = Field(default=5, ge=1, le=20, description="最多返回多少条命中片段。")


def create_paper_keyword_search_tool(full_markdown: str) -> ToolSpec:
    lines = full_markdown.splitlines()

    def handler(keyword: str, max_hits: int = 5) -> dict:
        normalized = keyword.strip().lower()
        hits: list[dict[str, str | int]] = []
        for index, line in enumerate(lines, start=1):
            if normalized and normalized in line.lower():
                hits.append(
                    {
                        "line_number": index,
                        "text": line.strip(),
                    }
                )
            if len(hits) >= max_hits:
                break
        return {"keyword": keyword, "hits": hits}

    return ToolSpec(
        name="paper_keyword_search",
        description="在论文全文 Markdown 中按关键词检索片段并返回命中行。",
        input_model=PaperKeywordSearchInput,
        handler=handler,
    )
