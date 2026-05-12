from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from review_engine import ReviewEngine


def _extract_title(markdown_text: str, fallback: str) -> str:
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def main() -> None:
    parser = argparse.ArgumentParser(description="运行固定维度论文评审工作流。")
    parser.add_argument("--paper", type=Path, required=True, help="输入 Markdown 文件路径。")
    parser.add_argument("--output", type=Path, default=Path("outputs"), help="输出目录。")
    args = parser.parse_args()

    paper_path = args.paper.expanduser().resolve()
    markdown_text = paper_path.read_text(encoding="utf-8")
    paper_id = paper_path.stem
    title = _extract_title(markdown_text, paper_id)

    engine = ReviewEngine()
    state = engine.run(
        paper_id=paper_id,
        thesis_title=title,
        full_markdown=markdown_text,
        input_path=str(paper_path),
        output_dir=str(args.output.expanduser().resolve()),
    )
    final_result = state.get("final_result") or {}
    print(final_result.get("summary", "评审已完成。"))
    print(final_result.get("markdown_path", ""))
    print(final_result.get("html_path", ""))
    print(final_result.get("state_path", ""))


if __name__ == "__main__":
    main()
