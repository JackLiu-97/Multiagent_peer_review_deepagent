from __future__ import annotations

import collections
import datetime
import importlib
import itertools
import json
import math
import re
import statistics
from typing import Any

from pydantic import BaseModel, Field

from review_engine.schemas import ToolSpec
from review_engine.utils import make_serializable


ALLOWED_IMPORTS = {
    "collections": collections,
    "datetime": datetime,
    "itertools": itertools,
    "json": json,
    "math": math,
    "re": re,
    "statistics": statistics,
}


class PythonAnalysisInput(BaseModel):
    code: str = Field(..., description="要执行的 Python 分析代码，结果放入 result 变量。")
    data: Any = Field(default=None, description="传入分析代码的数据对象。")


def _safe_import(
    name: str,
    globals_dict: dict[str, Any] | None = None,
    locals_dict: dict[str, Any] | None = None,
    fromlist: tuple[str, ...] | None = None,
    level: int = 0,
) -> Any:
    if level != 0:
        raise ImportError("Relative imports are not allowed in the analysis sandbox.")

    root_name = name.split(".", 1)[0]
    if root_name not in ALLOWED_IMPORTS:
        raise ImportError(f"Import `{name}` is not allowed in the analysis sandbox.")
    return importlib.import_module(name)


def create_python_analysis_tool() -> ToolSpec:
    def handler(code: str, data: Any = None) -> dict:
        local_vars = {
            "data": data,
            "collections": collections,
            "datetime": datetime,
            "itertools": itertools,
            "json": json,
            "math": math,
            "re": re,
            "statistics": statistics,
        }
        safe_builtins = {
            "__import__": _safe_import,
            "abs": abs,
            "all": all,
            "any": any,
            "dict": dict,
            "enumerate": enumerate,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "range": range,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
        }
        exec(code, {"__builtins__": safe_builtins}, local_vars)
        return {"result": make_serializable(local_vars.get("result"))}

    return ToolSpec(
        name="python_analysis_sandbox",
        description="在受限 Python 环境中对查询结果做聚合和统计，结果写入 result 变量。",
        input_model=PythonAnalysisInput,
        handler=handler,
    )
