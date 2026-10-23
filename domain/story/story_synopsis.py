"""Story Synopsis / 故事梗概模型。

Story Synopsis 的职责是把 Story Bible 的稳定设定转化为完整故事因果链：
故事从哪里开始、为什么推进、关键转折在哪里、人物如何变化、最终如何收束。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TurningPoint(BaseModel):
    """关键转折点，记录转折内容和它对后续剧情的影响。"""

    model_config = ConfigDict(extra="ignore")

    turning_point_id: str
    title: str
    description: str
    story_effect: str | None = None


class CharacterArcSummary(BaseModel):
    """核心人物变化摘要，避免在故事梗概里重复完整人物圣经。"""

    model_config = ConfigDict(extra="ignore")

    character_role: str
    arc: str


class StorySynopsis(BaseModel):
    """完整故事因果链。"""

    model_config = ConfigDict(extra="ignore")

    story_synopsis_id: str = "story_synopsis_v001"
    parent_artifact_id: str | None = "story_bible_v001"
    premise: str
    protagonist_goal: str
    main_story_arc: str
    major_turning_points: list[TurningPoint] = Field(default_factory=list)
    major_conflicts: list[str] = Field(default_factory=list)
    causal_chain: list[str] = Field(default_factory=list)
    character_arcs: list[CharacterArcSummary] = Field(default_factory=list)
    climax: str
    resolution: str

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_story_concept(cls, data: Any) -> Any:
        """兼容旧版 story_concept，让旧 prompt 偶发输出也能被解析。"""

        if not isinstance(data, dict):
            return data
        if "story_synopsis_id" in data:
            return data

        migrated = dict(data)
        if "story_concept_id" in migrated:
            migrated["story_synopsis_id"] = "story_synopsis_v001"
        premise = migrated.get("premise") or migrated.get("summary") or "故事前提待补充。"
        conflicts = migrated.get("conflict_ladder") or migrated.get("major_conflicts") or []
        migrated.setdefault("premise", premise)
        migrated.setdefault("protagonist_goal", "主角围绕核心冲突完成阶段性目标。")
        migrated.setdefault("main_story_arc", "故事围绕主角目标逐步升级，并在最终对抗中收束。")
        migrated.setdefault("major_turning_points", [])
        migrated.setdefault("major_conflicts", conflicts)
        migrated.setdefault("causal_chain", conflicts)
        migrated.setdefault("character_arcs", [])
        migrated.setdefault("climax", "主角在最终危机中完成决定性反击。")
        migrated.setdefault("resolution", "主线冲突收束，主角完成成长。")
        migrated.setdefault("parent_artifact_id", "story_bible_v001")
        return migrated
