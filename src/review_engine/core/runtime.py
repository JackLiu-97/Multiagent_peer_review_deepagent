from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from review_engine.core.deep_agents import StructuredDeepAgent
from review_engine.core.dimensions import DIMENSION_ORDER, get_dimension_config
from review_engine.core.prompts import (
    CRITIC_SYSTEM_PROMPT,
    SCORING_HISTORY_SUBAGENT_SYSTEM_PROMPT,
    SCORING_MAIN_SYSTEM_PROMPT,
)
from review_engine.core.settings import Settings, load_settings
from review_engine.formatters import render_html_report, render_markdown_report
from review_engine.logging import ArtifactManager, RunLogger
from review_engine.schemas import (
    CriticResult,
    RawReviewPayload,
    ScoringBundleResult,
    normalize_review_payload,
)
from review_engine.tools import (
    HistoryRepository,
    create_db_schema_inspect_tool,
    create_paper_excerpt_tool,
    create_paper_keyword_search_tool,
    create_python_analysis_tool,
    create_sql_readonly_tool,
)
from review_engine.utils import configure_logging, make_serializable


class WorkflowRuntime:
    """Owns one paper run: artifacts, logs, agents, and node-level business logic."""

    def __init__(self, settings: Settings, *, paper_id: str, output_dir: str | Path) -> None:
        self.settings = settings
        self.paper_id = paper_id
        self.run_id = f"review_{uuid.uuid4().hex[:12]}"
        self.run_dir = Path(output_dir).resolve() / paper_id
        self.artifacts = ArtifactManager(self.run_dir)
        self.logger = RunLogger(
            run_id=self.run_id,
            paper_stem=paper_id,
            log_path=self.run_dir / f"{paper_id}.log.jsonl",
            console=settings.console_log_enabled,
        )
        self.history_repository = HistoryRepository(settings.history_database_url)
        self.review_agents = {
            key: StructuredDeepAgent(
                settings=settings,
                artifact_manager=self.artifacts,
                logger=self.logger,
                agent_name=f"review_{key}",
            )
            for key in DIMENSION_ORDER
        }
        self.critic_agent = StructuredDeepAgent(
            settings=settings,
            artifact_manager=self.artifacts,
            logger=self.logger,
            agent_name="critic",
        )
        self.scoring_agent = StructuredDeepAgent(
            settings=settings,
            artifact_manager=self.artifacts,
            logger=self.logger,
            agent_name="scoring_main",
        )

    def initialize_state(self, state: dict[str, Any]) -> dict[str, Any]:
        input_artifact = self.artifacts.write_json(
            "paper_input.json",
            {
                "paper_id": state.get("paper_id", self.paper_id),
                "thesis_title": state.get("thesis_title", ""),
                "input_path": state.get("input_path", ""),
            },
        )
        self.artifacts.write_text("paper_source.md", state.get("full_markdown", ""))
        self.logger.log(
            event_type="run_started",
            message="Initializing review workflow state.",
            node_name="initialize_state",
            input_refs=[input_artifact],
        )
        return {
            "paper_id": state["paper_id"],
            "thesis_title": state["thesis_title"],
            "full_markdown": state["full_markdown"],
            "input_path": state.get("input_path", ""),
            "output_dir": str(self.run_dir.parent),
            "dimension_order": list(DIMENSION_ORDER),
            "pending_dimensions": list(DIMENSION_ORDER),
            "current_round": 1,
            "max_rounds": self.settings.max_review_rounds,
            "review_results": {},
            "review_history": {},
        }

    def dispatch_retry(self, state: dict[str, Any]) -> dict[str, Any]:
        critic_result = state.get("critic_result") or {}
        if not critic_result:
            self.logger.log(
                event_type="node_enter",
                message="Dispatching the initial fixed-dimension review wave.",
                node_name="dispatch_retry",
            )
            return {"pending_dimensions": list(state.get("dimension_order") or [])}

        failed_dimensions = list(critic_result.get("failed_dimensions") or [])
        if not failed_dimensions:
            return {"pending_dimensions": []}

        self.logger.log(
            event_type="node_enter",
            message="Dispatching only failed dimensions for another review round.",
            node_name="dispatch_retry",
            metadata={"round": int(state.get("current_round", 1)) + 1},
        )
        return {
            "pending_dimensions": failed_dimensions,
            "current_round": int(state.get("current_round", 1)) + 1,
        }

    def review_dimension(self, state: dict[str, Any], dimension_key: str) -> dict[str, Any]:
        pending_dimensions = set(state.get("pending_dimensions") or [])
        if dimension_key not in pending_dimensions:
            return {}

        dimension = get_dimension_config(dimension_key)
        round_no = int(state.get("current_round", 1))
        full_markdown = state.get("full_markdown", "")
        critic_feedback = (
            (state.get("critic_result") or {})
            .get("feedback_by_dimension", {})
            .get(dimension_key, "")
        )
        payload = {
            "paper_id": state.get("paper_id", ""),
            "thesis_title": state.get("thesis_title", ""),
            "review_dimension": dimension.label,
            "dimension_key": dimension.key,
            "review_scope": dimension.scope,
            "round": round_no,
            "critic_feedback": critic_feedback or None,
            "full_markdown": full_markdown,
        }
        tools = [
            create_paper_keyword_search_tool(full_markdown),
            create_paper_excerpt_tool(full_markdown),
        ]

        response, artifacts = self.review_agents[dimension_key].run_json(
            system_prompt=dimension.system_prompt,
            payload=payload,
            schema_model=RawReviewPayload,
            artifact_stem=f"reviews/{dimension_key}/round_{round_no:02d}",
            node_name="review_dimension",
            tools=tools,
        )
        normalized = normalize_review_payload(
            make_serializable(response),
            dimension=dimension.key,
            dimension_label=dimension.label,
            round_no=round_no,
        )

        result_artifact = self.artifacts.write_json(
            f"reviews/{dimension_key}/round_{round_no:02d}/normalized_result.json",
            normalized.model_dump(mode="json"),
        )
        history_item = {
            "round": round_no,
            "review": normalized.model_dump(mode="json"),
            "critic_feedback": critic_feedback,
        }
        output_refs = [
            result_artifact,
            artifacts.prompt_artifact,
            artifacts.input_artifact,
            artifacts.state_artifact,
        ]
        self.logger.log(
            event_type="node_exit",
            message=f"Completed {dimension.label} dimension review.",
            node_name="review_dimension",
            agent_role=dimension_key,
            output_refs=output_refs,
            metadata={"round": round_no, "dimension": dimension_key},
        )
        return {
            "review_results": {dimension_key: normalized.model_dump(mode="json")},
            "review_history": {dimension_key: [history_item]},
        }

    def collect_reviews(self, state: dict[str, Any]) -> dict[str, Any]:
        pending_dimensions = list(state.get("pending_dimensions") or [])
        review_results = dict(state.get("review_results") or {})
        missing_dimensions = [
            dimension for dimension in pending_dimensions if dimension not in review_results
        ]
        if not missing_dimensions:
            return {}

        self.logger.log(
            event_type="node_failed",
            message="Missing dimension outputs before critic stage.",
            node_name="collect_reviews",
            metadata={"dimension": ",".join(missing_dimensions)},
        )
        raise RuntimeError(
            "Missing review outputs for dimensions: " + ", ".join(missing_dimensions)
        )

    def run_critic(self, state: dict[str, Any]) -> dict[str, Any]:
        full_markdown = state.get("full_markdown", "")
        payload = {
            "paper_id": state.get("paper_id", ""),
            "thesis_title": state.get("thesis_title", ""),
            "round": state.get("current_round", 1),
            "review_results": state.get("review_results") or {},
            "full_markdown": full_markdown,
        }
        tools = [
            create_paper_keyword_search_tool(full_markdown),
            create_paper_excerpt_tool(full_markdown),
        ]
        round_no = int(state.get("current_round", 1))

        result, artifacts = self.critic_agent.run_json(
            system_prompt=CRITIC_SYSTEM_PROMPT,
            payload=payload,
            schema_model=CriticResult,
            artifact_stem=f"critic/round_{round_no:02d}",
            node_name="critic",
            tools=tools,
        )
        critic_result = result.model_dump(mode="json")
        critic_result["failed_dimensions"] = [
            key for key in critic_result.get("failed_dimensions", []) if key in DIMENSION_ORDER
        ]
        result_artifact = self.artifacts.write_json(
            f"critic/round_{round_no:02d}/critic_result.json",
            critic_result,
        )
        output_refs = [
            result_artifact,
            artifacts.prompt_artifact,
            artifacts.input_artifact,
            artifacts.state_artifact,
        ]
        self.logger.log(
            event_type="node_exit",
            message="Critic review completed.",
            node_name="critic",
            output_refs=output_refs,
            metadata={"round": round_no},
        )
        return {"critic_result": critic_result}

    def score_paper(self, state: dict[str, Any]) -> dict[str, Any]:
        if not self.history_repository.available:
            raise RuntimeError("History database is not configured or unavailable.")

        round_no = int(state.get("current_round", 1))
        subagents: list[dict[str, object]] = [
            {
                "name": "history_data_analyst",
                "description": "查询历史评分数据库，并返回用于分数校准的证据。",
                "system_prompt": SCORING_HISTORY_SUBAGENT_SYSTEM_PROMPT,
                "tools": [
                    create_db_schema_inspect_tool(self.history_repository),
                    create_sql_readonly_tool(self.history_repository),
                    create_python_analysis_tool(),
                ],
            }
        ]
        payload = {
            "paper_id": state.get("paper_id", ""),
            "thesis_title": state.get("thesis_title", ""),
            "round": round_no,
            "review_results": state.get("review_results") or {},
            "critic_result": state.get("critic_result") or {},
            "full_markdown": state.get("full_markdown", ""),
            "history_schema_hint": self.history_repository.schema_hint(),
            "history_agent_available": True,
        }

        result, artifacts = self.scoring_agent.run_json(
            system_prompt=SCORING_MAIN_SYSTEM_PROMPT,
            payload=payload,
            schema_model=ScoringBundleResult,
            artifact_stem=f"score/round_{round_no:02d}",
            node_name="score",
            subagents=subagents,
        )

        payload_result = result.model_dump(mode="json")
        score_artifact = self.artifacts.write_json(
            f"score/round_{round_no:02d}/score_bundle.json",
            payload_result,
        )
        output_refs = [
            score_artifact,
            artifacts.prompt_artifact,
            artifacts.input_artifact,
            artifacts.state_artifact,
        ]
        self.logger.log(
            event_type="node_exit",
            message="Scoring stage completed.",
            node_name="score",
            output_refs=output_refs,
            metadata={"round": round_no},
        )
        return {
            "base_score_result": payload_result.get("base_score_result", {}),
            "history_analysis_result": payload_result.get("history_analysis_result", {}),
            "final_score_result": payload_result.get("final_score_result", {}),
        }

    def format_report(self, state: dict[str, Any]) -> dict[str, Any]:
        markdown_report = render_markdown_report(state)
        html_report = render_html_report(markdown_report, state)
        markdown_artifact = self.artifacts.write_text("preview/review_report.md", markdown_report)
        html_artifact = self.artifacts.write_text("preview/review_report.html", html_report)
        self.logger.log(
            event_type="node_exit",
            message="Rendered markdown and HTML review previews.",
            node_name="formatter",
            output_refs=[markdown_artifact, html_artifact],
        )
        return {
            "formatted_report_markdown": markdown_report,
            "formatted_report_html": html_report,
        }

    def export_result(self, state: dict[str, Any]) -> dict[str, Any]:
        paper_id = state.get("paper_id", self.paper_id)
        markdown_path = self.artifacts.write_text(
            f"{paper_id}_review.md", state.get("formatted_report_markdown", "")
        )
        html_path = self.artifacts.write_text(
            f"{paper_id}_review.html", state.get("formatted_report_html", "")
        )
        state_path = self.artifacts.write_text(
            f"{paper_id}_state.json",
            json.dumps(make_serializable(state), ensure_ascii=False, indent=2),
        )

        final_score = state.get("final_score_result") or {}
        critic_result = state.get("critic_result") or {}
        final_result = {
            "paper_id": paper_id,
            "final_score": final_score.get("final_score", 0),
            "critic_approved": critic_result.get("approved", False),
            "review_rounds_used": state.get("current_round", 1),
            "markdown_path": markdown_path,
            "html_path": html_path,
            "state_path": state_path,
            "summary": f"评审完成。最终建议得分：{final_score.get('final_score', 0)}分。",
        }
        result_artifact = self.artifacts.write_json("final_result.json", final_result)
        self.logger.log(
            event_type="run_finished",
            message="Final review artifacts saved.",
            node_name="export_result",
            output_refs=[markdown_path, html_path, state_path, result_artifact],
        )
        return {"final_result": final_result}


class ReviewEngine:
    """Top-level engine that builds a paper-scoped runtime and invokes the workflow."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        configure_logging(self.settings.log_level)

    def run(
        self,
        *,
        paper_id: str,
        thesis_title: str,
        full_markdown: str,
        input_path: str = "",
        output_dir: str | None = None,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        from review_engine.workflows.review_graph import build_review_workflow

        output_root = output_dir or self.settings.default_output_dir
        runtime = WorkflowRuntime(self.settings, paper_id=paper_id, output_dir=output_root)
        workflow = build_review_workflow(runtime, self.settings)
        initial_state = {
            "paper_id": paper_id,
            "thesis_title": thesis_title,
            "full_markdown": full_markdown,
            "input_path": input_path,
            "output_dir": str(Path(output_root).resolve()),
        }
        config = {
            "configurable": {"thread_id": thread_id or f"review_{paper_id}"},
            "recursion_limit": 80,
        }
        try:
            final_state = workflow.invoke(initial_state, config=config)
        except Exception as exc:
            runtime.logger.log(
                event_type="run_failed",
                message=f"Workflow failed: {exc}",
                node_name="workflow",
                input_refs=[input_path] if input_path else [],
                metadata={"error_type": type(exc).__name__},
            )
            raise
        runtime.logger.log(
            event_type="run_completed",
            message="Workflow completed successfully.",
            node_name="workflow",
            output_refs=[(final_state.get("final_result") or {}).get("state_path", "")],
        )
        return final_state
