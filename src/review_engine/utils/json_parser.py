from __future__ import annotations

import json
from typing import Any, Type

from pydantic import BaseModel


def extract_json_text(text: str) -> str:
    body = (text or "").strip()
    if not body:
        raise ValueError("empty response")

    if "```" in body:
        parts = body.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") or candidate.startswith("["):
                body = candidate
                break

    start_obj = body.find("{")
    end_obj = body.rfind("}")
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        return body[start_obj : end_obj + 1]

    start_arr = body.find("[")
    end_arr = body.rfind("]")
    if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        return body[start_arr : end_arr + 1]

    raise ValueError("no json payload found")


def parse_model_response(text: str, model_cls: Type[BaseModel]) -> BaseModel:
    json_text = extract_json_text(text)
    return model_cls.model_validate(json.loads(json_text))


def make_serializable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_serializable(v) for v in obj]
    if isinstance(obj, tuple):
        return [make_serializable(v) for v in obj]
    if hasattr(obj, "model_dump"):
        return make_serializable(obj.model_dump())
    return obj


def to_pretty_json(obj: Any) -> str:
    return json.dumps(make_serializable(obj), ensure_ascii=False, indent=2)
