<div align="center">

# Multiagent Peer Review DeepAgent

**A fixed-dimension thesis review workflow powered by LangGraph and Deep Agents.**

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-workflow-1f6feb?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![Deep Agents](https://img.shields.io/badge/Deep%20Agents-review%20agents-6f42c1?style=flat-square)](https://github.com/langchain-ai/deepagents)

</div>

## Overview

Multiagent Peer Review DeepAgent is an experimental review engine for academic thesis evaluation. It splits a paper into fixed review dimensions, runs specialized Deep Agents for each dimension, validates their outputs with a critic stage, and produces a calibrated final score with Markdown and HTML reports.

The workflow is designed for repeatable, inspectable review runs:

- **Fixed review dimensions**: abstract, introduction, methods, and references.
- **Multi-agent execution**: one structured review agent per dimension.
- **Critic loop**: failed or inconsistent dimensions can be retried.
- **Score calibration**: optional historical database lookup for score distribution and common issue patterns.
- **Traceable artifacts**: prompts, inputs, intermediate states, logs, reports, and final result files are written under an output directory.

> This project can process sensitive papers and API credentials. Read the [Privacy And Publishing Notes](#privacy-and-publishing-notes) before pushing to GitHub.

## Architecture

```text
Markdown paper
      |
      v
Initialize run state
      |
      v
Dimension review agents
  - abstract
  - introduction
  - methods
  - references
      |
      v
Critic validation and retry dispatch
      |
      v
Scoring and optional history calibration
      |
      v
Markdown / HTML report export
```

## Requirements

- Python 3.12 or newer
- An OpenAI-compatible API key
- `uv` is recommended for dependency management

Core dependencies are declared in [`pyproject.toml`](pyproject.toml):

- `deepagents`
- `langchain`
- `langchain-openai`
- `langgraph`
- `pydantic`
- `sqlalchemy`
- `pymysql`

## Quick Start

Clone the repository and install dependencies:

```powershell
uv sync
```

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and fill in your API key:

```dotenv
OPENAI_API_KEY=your_api_key_here
DEEPAGENT_MODEL=gpt-4o-mini
```

Run the sample paper:

```powershell
uv run python main.py --paper examples/sample_paper.md --output outputs
```

Or use the installed console script:

```powershell
uv run review-engine --paper examples/sample_paper.md --output outputs
```

After a successful run, results are written to:

```text
outputs/sample_paper/
```

## Configuration

Configuration is loaded from `.env` and process environment variables. Environment variables override values in `.env`.

| Variable | Required | Description |
| --- | --- | --- |
| `DEEPAGENT_MODEL` | No | Model name used by the review, critic, and scoring agents. |
| `OPENAI_API_KEY` | Yes | API key for the OpenAI-compatible model provider. |
| `DEEPAGENT_API_KEY` | No | Alternative API key variable. Used if set. |
| `OPENAI_BASE_URL` | No | Optional OpenAI-compatible base URL. |
| `DEEPAGENT_BASE_URL` | No | Alternative base URL variable. Used if set. |
| `MAX_REVIEW_ROUNDS` | No | Maximum critic retry rounds. Default: `2`. |
| `MAX_TOOL_ROUNDS` | No | Maximum internal tool rounds. Default: `6`. |
| `HISTORY_DATABASE_URL` | No | Optional SQLAlchemy database URL for historical score calibration. |
| `HISTORY_SCHEMA_NAME` | No | Optional schema name for history lookup. |
| `REVIEW_OUTPUT_DIR` | No | Default output directory. Default: `outputs`. |
| `LOG_LEVEL` | No | Python logging level. Default: `INFO`. |
| `CONSOLE_LOG_ENABLED` | No | Whether to print workflow logs to the console. |

Do not commit `.env`. Commit `.env.example` only.

## Usage

### Command Line

```powershell
uv run python main.py --paper <path-to-paper.md> --output <output-dir>
```

Arguments:

| Argument | Required | Description |
| --- | --- | --- |
| `--paper` | Yes | Path to the input Markdown paper. |
| `--output` | No | Directory for generated artifacts. Default: `outputs`. |

The paper ID is inferred from the input file name. The title is inferred from the first Markdown heading.

### Python API

```python
from pathlib import Path

from review_engine import ReviewEngine

paper_path = Path("examples/sample_paper.md")
markdown_text = paper_path.read_text(encoding="utf-8")

engine = ReviewEngine()
state = engine.run(
    paper_id=paper_path.stem,
    thesis_title="Sample Paper",
    full_markdown=markdown_text,
    input_path=str(paper_path),
    output_dir="outputs",
)

print(state["final_result"])
```

## Output Structure

A run creates one paper-specific directory:

```text
outputs/<paper_id>/
  paper_input.json
  paper_source.md
  <paper_id>.log.jsonl
  reviews/
  critic/
  score/
  artifacts/
  preview/
    review_report.md
    review_report.html
  <paper_id>_review.md
  <paper_id>_review.html
  <paper_id>_state.json
  final_result.json
```

Important files:

| File | Description |
| --- | --- |
| `final_result.json` | Compact run summary, final score, approval status, and report paths. |
| `<paper_id>_review.md` | Final Markdown review report. |
| `<paper_id>_review.html` | Final HTML review report. |
| `<paper_id>_state.json` | Full workflow state for debugging and audit. |
| `<paper_id>.log.jsonl` | Structured event log for the run. |
| `artifacts/**` | Prompt snapshots, agent inputs, and agent states. |

Generated outputs can contain private paper text, prompts, model responses, local paths, and database-derived context. They are ignored by Git by default.

## Project Layout

```text
.
  main.py                         # CLI wrapper
  pyproject.toml                  # Package metadata and dependencies
  .env.example                    # Safe environment template
  examples/
    sample_paper.md               # Public toy input
  src/review_engine/
    core/                         # Runtime, settings, dimensions, prompts
    workflows/                    # LangGraph workflow wiring
    agents/                       # Deep agent runner compatibility layer
    schemas/                      # Structured review and scoring models
    tools/                        # Paper search, excerpt, SQL, and analysis tools
    formatters/                   # Markdown and HTML report renderers
    logging/                      # Artifact and event logging
```

## Privacy And Publishing Notes

Before publishing this repository, keep these rules:

- Never commit `.env`, `.env.*`, real API keys, database credentials, private certificates, or SSH keys.
- Never commit `outputs*` directories. They can contain full paper content, prompts, responses, logs, and local absolute paths.
- Keep only safe toy examples in `examples/`. Real paper files matching `examples/paper_*.md` are ignored by default.
- Do not publish local databases, exported spreadsheets, CSV files, or private datasets.
- Run a dry-run check before committing:

```powershell
git add --dry-run .
git status --ignored
```

If a secret was ever committed or pushed, remove it from history and rotate the credential immediately.

## Troubleshooting

### `Missing DEEPAGENT_API_KEY or OPENAI_API_KEY`

Create `.env` from `.env.example` and set `OPENAI_API_KEY` or `DEEPAGENT_API_KEY`.

### Model or endpoint errors

Check `DEEPAGENT_MODEL`, `OPENAI_BASE_URL`, and `DEEPAGENT_BASE_URL`. The project uses `langchain-openai`, so the provider must expose an OpenAI-compatible chat completion interface.

### Empty history calibration

`HISTORY_DATABASE_URL` is optional. If it is not set, the workflow still runs, but historical score calibration has no database context.

## License

No license file is currently included. Add a license before publishing if you want others to use, modify, or redistribute the project.
