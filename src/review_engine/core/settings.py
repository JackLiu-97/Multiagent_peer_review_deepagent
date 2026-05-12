from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class Settings(BaseModel):
    """Central runtime settings loaded from `.env` and process environment."""

    deepagent_model: str = "gpt-4o-mini"
    deepagent_api_key: str | None = None
    deepagent_base_url: str | None = None
    max_review_rounds: int = 2
    max_tool_rounds: int = 6
    history_database_url: str = ""
    history_schema_name: str = ""
    default_output_dir: str = "outputs"
    log_level: str = "INFO"
    console_log_enabled: bool = True

    @classmethod
    def from_env(cls, env_path: str | Path = ".env", **overrides: Any) -> "Settings":
        raw = cls._load_env_file(env_path)
        merged = {**raw, **os.environ}
        data = {
            "deepagent_model": (
                cls._pick(merged, "DEEPAGENT_MODEL", "SMART_MODEL", "OPENAI_MODEL")
                or "gpt-4o-mini"
            ),
            "deepagent_api_key": cls._pick(merged, "DEEPAGENT_API_KEY", "OPENAI_API_KEY"),
            "deepagent_base_url": cls._pick(merged, "DEEPAGENT_BASE_URL", "OPENAI_BASE_URL"),
            "max_review_rounds": cls._as_int(cls._pick(merged, "MAX_REVIEW_ROUNDS"), 2),
            "max_tool_rounds": cls._as_int(cls._pick(merged, "MAX_TOOL_ROUNDS"), 6),
            "history_database_url": cls._pick(merged, "HISTORY_DATABASE_URL") or "",
            "history_schema_name": cls._pick(merged, "HISTORY_SCHEMA_NAME") or "",
            "default_output_dir": cls._pick(merged, "REVIEW_OUTPUT_DIR") or "outputs",
            "log_level": (cls._pick(merged, "LOG_LEVEL") or "INFO").upper(),
            "console_log_enabled": cls._as_bool(cls._pick(merged, "CONSOLE_LOG_ENABLED"), True),
        }
        data.update(overrides)
        return cls(**data)

    @staticmethod
    def _load_env_file(env_path: str | Path) -> dict[str, str]:
        path = Path(env_path)
        if not path.exists():
            return {}

        values: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
        return values

    @staticmethod
    def _pick(values: dict[str, str], *keys: str) -> str | None:
        for key in keys:
            if key in values and str(values[key]).strip():
                return str(values[key]).strip()
        return None

    @staticmethod
    def _as_bool(value: str | None, default: bool) -> bool:
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _as_int(value: str | None, default: int) -> int:
        try:
            return int(value) if value is not None else default
        except ValueError:
            return default

    def to_env_dict(self) -> dict[str, str]:
        env = {
            "DEEPAGENT_MODEL": self.deepagent_model,
            "MAX_REVIEW_ROUNDS": str(self.max_review_rounds),
            "MAX_TOOL_ROUNDS": str(self.max_tool_rounds),
            "REVIEW_OUTPUT_DIR": self.default_output_dir,
        }
        if self.deepagent_api_key:
            env["OPENAI_API_KEY"] = self.deepagent_api_key
            env["DEEPAGENT_API_KEY"] = self.deepagent_api_key
        if self.deepagent_base_url:
            env["OPENAI_BASE_URL"] = self.deepagent_base_url
            env["DEEPAGENT_BASE_URL"] = self.deepagent_base_url
        if self.history_database_url:
            env["HISTORY_DATABASE_URL"] = self.history_database_url
        return env


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[3]
    return Settings.from_env(project_root / ".env")
