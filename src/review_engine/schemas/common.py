from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel


@dataclass
class ToolSpec:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[..., Any]

    def invoke(self, arguments: dict[str, Any]) -> Any:
        payload = self.input_model.model_validate(arguments)
        return self.handler(**payload.model_dump())
