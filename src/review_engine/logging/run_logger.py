from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from review_engine.logging.event_schema import RunLogEvent


class RunLogger:
    """Write JSONL logs and concise console updates for one workflow run."""

    def __init__(self, run_id: str, paper_stem: str, log_path: Path, console: bool = True) -> None:
        self.run_id = run_id
        self.paper_stem = paper_stem
        self.log_path = log_path
        self.console = console
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        *,
        event_type: str,
        message: str,
        node_name: str,
        agent_role: str | None = None,
        input_refs: list[str] | None = None,
        output_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = RunLogEvent(
            ts=datetime.now(UTC).isoformat(),
            run_id=self.run_id,
            paper_stem=self.paper_stem,
            node_name=node_name,
            agent_role=agent_role,
            event_type=event_type,
            message=message,
            input_refs=input_refs or [],
            output_refs=output_refs or [],
            metadata=metadata or {},
        )
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")
        self._emit_console(event)

    def _emit_console(self, event: RunLogEvent) -> None:
        if not self.console:
            return

        timestamp = event.ts[11:19] if "T" in event.ts else event.ts
        role = f"/{event.agent_role}" if event.agent_role else ""
        ref_summary = self._format_ref_summary(event)
        metadata_summary = self._format_metadata_summary(event.metadata)
        line = f"[{timestamp}] [{event.node_name}{role}] {event.message}"
        if ref_summary:
            line = f"{line} | {ref_summary}"
        if metadata_summary:
            line = f"{line} | {metadata_summary}"
        print(line, file=sys.stderr, flush=True)

    @staticmethod
    def _format_ref_summary(event: RunLogEvent) -> str:
        if event.output_refs:
            return f"outputs={len(event.output_refs)}"
        if event.input_refs:
            return f"inputs={len(event.input_refs)}"
        return ""

    @staticmethod
    def _format_metadata_summary(metadata: dict[str, Any]) -> str:
        interesting_keys = ("round", "dimension", "workspace", "rows", "query_count", "error_type")
        parts: list[str] = []
        for key in interesting_keys:
            value = metadata.get(key)
            if value in (None, "", [], {}):
                continue
            parts.append(f"{key}={value}")
        return ", ".join(parts)
