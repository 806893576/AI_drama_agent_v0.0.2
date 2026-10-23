"""Story Bible / 世界观圣经模型。

Story Bible 只保存后续所有创作都必须遵守的“稳定设定层”：
标题、完整设定摘要、主题、世界/叙事规则、核心冲突、时间线规则和不可变事实。
具体故事因果链交给 Story Synopsis 负责，避免一个模型承担过多职责。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StoryBible(BaseModel):
    """故事圣经。

    summary 是完整摘要，不再是一句话 logline；它用于让下游快速理解故事设定边界。
    兼容层会把旧版 logline 映射到 summary，但新代码不再主动写入 logline/emotional_promise。
    """

    model_config = ConfigDict(extra="ignore")

    story_bible_id: str
    title: str | None = None
    summary: str
    theme: str
    world_rules: list[str] = Field(default_factory=list)
    core_conflict: str
    timeline_rules: list[str] = Field(default_factory=list)
    immutable_facts: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict) and "summary" not in data and "logline" in data:
            data = dict(data)
            data["summary"] = data.pop("logline")
            data.pop("emotional_promise", None)
        return data
