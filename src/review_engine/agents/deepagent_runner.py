from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence, Type

from pydantic import BaseModel

from review_engine.core.deep_agents import StructuredDeepAgent
from review_engine.core.settings import Settings
from review_engine.logging import ArtifactManager, RunLogger
from review_engine.schemas import ToolSpec


class DeepAgentRunner:
    """Compatibility shim that forwards the old runner API to `StructuredDeepAgent`."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        run_root = Path(settings.default_output_dir).resolve() / ".legacy_runner"
        self.artifacts = ArtifactManager(run_root)
        self.logger = RunLogger(
            run_id=f"legacy_{uuid.uuid4().hex[:12]}",
            paper_stem="legacy_runner",
            log_path=run_root / "legacy_runner.log.jsonl",
            console=False,
        )

    def run_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_model: Type[BaseModel],
        tools: Sequence[ToolSpec] | None = None,
        subagents: Sequence[Mapping[str, Any]] | None = None,
        agent_name: str | None = None,
    ) -> BaseModel:
        agent = StructuredDeepAgent(
            settings=self.settings,
            artifact_manager=self.artifacts,
            logger=self.logger,
            agent_name=agent_name or "legacy_deep_agent",
        )
        result, _ = agent.run_json(
            system_prompt=system_prompt,
            payload={"user_prompt": user_prompt},
            schema_model=schema_model,
            artifact_stem=f"{agent_name or 'legacy'}/{uuid.uuid4().hex[:8]}",
            node_name="legacy_run_json",
            tools=tools,
            subagents=subagents,
        )
        return result
