from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Type

from pydantic import BaseModel

from review_engine.core.settings import Settings
from review_engine.logging import ArtifactManager, RunLogger
from review_engine.schemas import ToolSpec
from review_engine.utils import make_serializable, parse_model_response


@dataclass(slots=True)
class DeepAgentRunArtifacts:
    prompt_artifact: str
    input_artifact: str
    state_artifact: str
    created_files: list[str]


class StructuredDeepAgent:
    """Thin wrapper over LangChain official Deep Agents with artifact logging."""

    def __init__(
        self,
        *,
        settings: Settings,
        artifact_manager: ArtifactManager,
        logger: RunLogger,
        agent_name: str,
    ) -> None:
        self.settings = settings
        self.artifact_manager = artifact_manager
        self.logger = logger
        self.agent_name = agent_name

    def run_json(
        self,
        *,
        system_prompt: str,
        payload: Mapping[str, Any],
        schema_model: Type[BaseModel],
        artifact_stem: str,
        node_name: str,
        tools: Sequence[ToolSpec] | None = None,
        subagents: Sequence[Mapping[str, Any]] | None = None,
    ) -> tuple[BaseModel, DeepAgentRunArtifacts]:
        prompt_artifact = self.artifact_manager.write_json(
            f"artifacts/{artifact_stem}/prompt_snapshot.json",
            {
                "agent_name": self.agent_name,
                "system_prompt": system_prompt,
                "subagents": [
                    {
                        "name": spec.get("name"),
                        "description": spec.get("description"),
                        "system_prompt": spec.get("system_prompt"),
                    }
                    for spec in (subagents or [])
                ],
            },
        )
        input_artifact = self.artifact_manager.write_json(
            f"artifacts/{artifact_stem}/agent_input.json",
            make_serializable(dict(payload)),
        )
        self.logger.log(
            event_type="deep_agent_started",
            message=f"Running deep agent `{self.agent_name}`.",
            node_name=node_name,
            agent_role=self.agent_name,
            input_refs=[input_artifact],
        )
        result, raw_state = self._run_with_official_deepagents(
            system_prompt=system_prompt,
            payload=payload,
            schema_model=schema_model,
            tools=tools or [],
            subagents=subagents or [],
        )
        created_files: list[str] = []

        state_artifact = self.artifact_manager.write_json(
            f"artifacts/{artifact_stem}/agent_state.json",
            {
                "structured_response": make_serializable(result),
                "created_files": created_files,
                "messages": self._serialize_messages(raw_state.get("messages", [])),
            },
        )
        self.logger.log(
            event_type="deep_agent_finished",
            message=f"Deep agent `{self.agent_name}` finished.",
            node_name=node_name,
            agent_role=self.agent_name,
            output_refs=[prompt_artifact, state_artifact, *created_files],
        )
        return result, DeepAgentRunArtifacts(
            prompt_artifact=prompt_artifact,
            input_artifact=input_artifact,
            state_artifact=state_artifact,
            created_files=created_files,
        )

    def _run_with_official_deepagents(
        self,
        *,
        system_prompt: str,
        payload: Mapping[str, Any],
        schema_model: Type[BaseModel],
        tools: Sequence[ToolSpec],
        subagents: Sequence[Mapping[str, Any]],
    ) -> tuple[BaseModel, dict[str, Any]]:
        try:
            from deepagents import create_deep_agent
            from langchain_openai import ChatOpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("Missing deepagents or langchain_openai dependency") from exc

        if not self.settings.deepagent_api_key:
            raise RuntimeError("Missing DEEPAGENT_API_KEY or OPENAI_API_KEY")

        model = ChatOpenAI(
            model=self.settings.deepagent_model,
            api_key=self.settings.deepagent_api_key,
            base_url=self.settings.deepagent_base_url or None,
            temperature=0.2,
        )
        agent = create_deep_agent(
            model=model,
            tools=self._to_langchain_tools(tools),
            system_prompt=system_prompt,
            subagents=self._to_deepagents_subagents(subagents),
            response_format=schema_model,
            name=self.agent_name,
        )
        raw_state = agent.invoke({"messages": [{"role": "user", "content": self._format_payload(payload)}]})
        structured = raw_state.get("structured_response") if isinstance(raw_state, dict) else None
        if structured is not None:
            if isinstance(structured, schema_model):
                return structured, raw_state
            if isinstance(structured, BaseModel):
                return schema_model.model_validate(structured.model_dump()), raw_state
            return schema_model.model_validate(structured), raw_state

        raw_content = self._extract_last_ai_content(raw_state)
        if not raw_content:
            raise RuntimeError("Deep agent returned neither structured_response nor assistant content")
        return parse_model_response(raw_content, schema_model), raw_state

    def _to_langchain_tools(self, tools: Sequence[ToolSpec]) -> list[Any]:
        if not tools:
            return []

        from langchain_core.tools import StructuredTool

        return [
            StructuredTool.from_function(
                func=tool.handler,
                name=tool.name,
                description=tool.description,
                args_schema=tool.input_model,
            )
            for tool in tools
        ]

    def _to_deepagents_subagents(
        self,
        subagents: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        if not subagents:
            return []

        try:
            from langchain_openai import ChatOpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("Missing langchain_openai dependency") from exc

        processed: list[dict[str, Any]] = []
        for raw_spec in subagents:
            spec = dict(raw_spec)
            raw_tools = spec.get("tools") or []
            converted_tools: list[Any] = []
            for tool in raw_tools:
                if isinstance(tool, ToolSpec):
                    converted_tools.extend(self._to_langchain_tools([tool]))
                else:
                    converted_tools.append(tool)
            spec["tools"] = converted_tools
            if spec.get("model") is None:
                spec["model"] = ChatOpenAI(
                    model=self.settings.deepagent_model,
                    api_key=self.settings.deepagent_api_key,
                    base_url=self.settings.deepagent_base_url or None,
                    temperature=0.2,
                )
            processed.append(spec)
        return processed

    @staticmethod
    def _format_payload(payload: Mapping[str, Any]) -> str:
        return "Task payload:\n" + json.dumps(make_serializable(dict(payload)), ensure_ascii=False, indent=2)

    @staticmethod
    def _serialize_messages(messages: Any) -> list[dict[str, Any]]:
        try:
            from langchain_core.messages import message_to_dict
        except Exception:  # pragma: no cover
            return [{"repr": repr(message)} for message in messages or []]

        serialized: list[dict[str, Any]] = []
        for message in messages or []:
            try:
                serialized.append(message_to_dict(message))
            except Exception:
                serialized.append({"repr": repr(message)})
        return serialized

    def _extract_last_ai_content(self, result: Any) -> str:
        if not isinstance(result, dict):
            return ""
        messages = result.get("messages") or []
        for message in reversed(messages):
            message_type = getattr(message, "type", "")
            if message_type == "ai":
                return self._normalize_message_content(getattr(message, "content", ""))
            if isinstance(message, dict) and message.get("role") == "assistant":
                return self._normalize_message_content(message.get("content", ""))
        return ""

    @staticmethod
    def _normalize_message_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
            return "\n".join(parts)
        return str(content)
