"""Character Bible / 人物圣经模型。

这里采用“轻量结构化”：人物圣经只保留完成后续剧本、分镜、美术和资产登记所需的
核心人物卡与关系卡。分集出场、关系逐集弧线、欲望/恐惧/价值观等更细拆项，交给
分集大纲或后续资产细化节点处理，降低真实 LLM 输出 JSON 的失败率。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CharacterProfile(BaseModel):
    """单角色核心卡。

    role 使用 protagonist / antagonist / ally 等稳定英文枚举式文本；
    motivation、character_arc 使用短段落，避免过度结构化和交叉引用。
    """

    model_config = ConfigDict(extra="ignore")

    character_id: str
    name: str
    role: str
    identity: str | None = None
    personality: list[str] = Field(default_factory=list)
    motivation: str
    external_goal: str
    internal_goal: str | None = None
    voice_style: str
    visual_keywords: list[str] = Field(default_factory=list)
    story_function: str | None = None
    character_arc: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        migrated = dict(data)
        migrated.setdefault("role", migrated.pop("role_type", None))
        migrated.setdefault("external_goal", migrated.pop("desire", None))
        migrated.setdefault("character_arc", migrated.pop("arc", None))
        migrated.setdefault("identity", migrated.pop("age_range", None))
        migrated.setdefault("role", "supporting")
        migrated.setdefault("external_goal", "完成其在主线中的阶段性目标。")
        migrated.setdefault(
            "motivation",
            migrated.get("external_goal") or "推动其在主线中的必要行动。",
        )
        migrated.setdefault("voice_style", "短句明确，符合人物处境。")
        return migrated

    @property
    def role_type(self) -> str:
        """兼容旧代码中 character.role_type 的读取。"""

        return self.role

    @property
    def desire(self) -> str:
        """兼容旧代码中 character.desire 的读取。"""

        return self.external_goal


class CharacterRelationship(BaseModel):
    """人物关系核心卡。

    关系保持轻量：稳定关系 ID、双方角色 ID、关系类型、关系说明和变化方向。
    """

    model_config = ConfigDict(extra="ignore")

    relationship_id: str | None = None
    source_character_id: str
    target_character_id: str
    type: str
    description: str | None = None
    change_arc: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        migrated = dict(data)
        migrated.setdefault("type", migrated.pop("relationship_type", None))
        reasons = migrated.pop("reason", None)
        if isinstance(reasons, list) and reasons and not migrated.get("description"):
            migrated["description"] = "；".join(str(item) for item in reasons)
        conflict = migrated.pop("conflict", None)
        dynamic = migrated.pop("emotional_dynamic", None)
        if conflict and not migrated.get("description"):
            migrated["description"] = str(conflict)
        if dynamic and not migrated.get("change_arc"):
            migrated["change_arc"] = str(dynamic)
        initial_state = migrated.pop("initial_state", None)
        current_state = migrated.pop("current_state", None)
        if (initial_state or current_state) and not migrated.get("change_arc"):
            migrated["change_arc"] = (
                f"{initial_state or '初始未明'} -> {current_state or '当前未明'}"
            )
        migrated.setdefault("type", "unknown")
        return migrated

    @property
    def relationship_type(self) -> str:
        """兼容旧代码中 relationship.relationship_type 的读取。"""

        return self.type


class CharacterGroup(BaseModel):
    """人物阵营或功能分组。"""

    model_config = ConfigDict(extra="ignore")

    group_id: str
    name: str
    type: str
    members: list[str] = Field(default_factory=list)


class CharacterBible(BaseModel):
    """角色圣经/人物系统。"""

    model_config = ConfigDict(extra="ignore")

    character_bible_id: str
    artifact_type: str = "character_bible"
    version: int = 1
    parent_artifact_id: str | None = "story_synopsis_v001"
    characters: list[CharacterProfile] = Field(default_factory=list)
    relationships: list[CharacterRelationship] = Field(default_factory=list)
    character_groups: list[CharacterGroup] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _unwrap_content(cls, data: Any) -> Any:
        if isinstance(data, dict) and "content" in data:
            content = dict(data["content"] or {})
            for key in ("character_bible_id", "artifact_type", "version", "parent_artifact_id"):
                if key in data:
                    content[key] = data[key]
            return content
        return data
