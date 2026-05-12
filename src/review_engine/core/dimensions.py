from __future__ import annotations

from dataclasses import dataclass

from review_engine.core.prompts import get_dimension_system_prompt


@dataclass(frozen=True)
class DimensionConfig:
    key: str
    label: str
    weight: int
    system_prompt: str
    scope: str


DIMENSIONS = {
    "abstract": DimensionConfig(
        key="abstract",
        label="摘要",
        weight=20,
        system_prompt=get_dimension_system_prompt("abstract"),
        scope="只从摘要完整性、表达清晰度、信息充分性和摘要写作质量进行评审。",
    ),
    "introduction": DimensionConfig(
        key="introduction",
        label="绪论",
        weight=25,
        system_prompt=get_dimension_system_prompt("introduction"),
        scope="只从研究背景、问题定义、研究动机、研究空白与贡献表述进行评审。",
    ),
    "methods": DimensionConfig(
        key="methods",
        label="相关工作与方法",
        weight=35,
        system_prompt=get_dimension_system_prompt("methods"),
        scope="只从相关工作、方法设计、自洽性、可复现性和论证支撑进行评审。",
    ),
    "references": DimensionConfig(
        key="references",
        label="参考文献",
        weight=20,
        system_prompt=get_dimension_system_prompt("references"),
        scope="只从参考文献质量、代表性、时效性和引文对应关系进行评审。",
    ),
}


DIMENSION_ORDER = ["abstract", "introduction", "methods", "references"]


def get_dimension_config(key: str) -> DimensionConfig:
    if key not in DIMENSIONS:
        raise KeyError(f"Unknown dimension: {key}")
    return DIMENSIONS[key]
