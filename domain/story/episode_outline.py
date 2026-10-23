"""Episode Outline / 分集大纲模型。

分集大纲负责把“完整故事 + 人物系统”切割成具体集数：
每集为什么存在、讲什么、谁参与、冲突是什么、爽点在哪里、如何转折并钩住下一集。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EpisodeOutline(BaseModel):
    """单集大纲。"""

    model_config = ConfigDict(extra="ignore")

    episode_id: str
    episode_number: int
    title: str | None = None
    basic_info: dict[str, Any] = Field(default_factory=dict)
    episode_positioning: str
    opening_hook: str
    core_conflict: str
    key_events: list[str] = Field(default_factory=list)
    characters_and_relationship_changes: list[dict[str, Any]] = Field(default_factory=list)
    emotional_beats: list[str] = Field(default_factory=list)
    turning_point_and_climax: str | None = None
    ending_and_cliffhanger: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        migrated = dict(data)
        migrated.setdefault("opening_hook", migrated.pop("hook", None))
        migrated.setdefault("core_conflict", migrated.pop("main_conflict", None))
        migrated.setdefault("turning_point_and_climax", migrated.pop("reversal", None))
        migrated.setdefault("ending_and_cliffhanger", migrated.pop("cliffhanger", None))
        emotional_peak = migrated.pop("emotional_peak", None)
        if emotional_peak and not migrated.get("emotional_beats"):
            migrated["emotional_beats"] = [emotional_peak]
        migrated.setdefault("episode_positioning", "推动主线阶段性升级。")
        migrated.setdefault("opening_hook", "以强冲突开场。")
        migrated.setdefault("core_conflict", "主角目标遭遇阶段性阻力。")
        return migrated

    @property
    def hook(self) -> str:
        """兼容旧代码中 outline.hook 的读取。"""

        return self.opening_hook

    @property
    def main_conflict(self) -> str:
        """兼容旧代码中 outline.main_conflict 的读取。"""

        return self.core_conflict

    @property
    def reversal(self) -> str | None:
        """兼容旧代码中 outline.reversal 的读取。"""

        return self.turning_point_and_climax

    @property
    def cliffhanger(self) -> str | None:
        """兼容旧代码中 outline.cliffhanger 的读取。"""

        return self.ending_and_cliffhanger

    @property
    def emotional_peak(self) -> str | None:
        """兼容旧代码中 outline.emotional_peak 的读取。"""

        return self.emotional_beats[-1] if self.emotional_beats else None


class EpisodeOutlinePackage(BaseModel):
    """分集大纲包。"""

    model_config = ConfigDict(extra="ignore")

    outline_package_id: str
    parent_artifact_ids: list[str] = Field(
        default_factory=lambda: ["story_bible_v001", "story_synopsis_v001", "character_bible_v001"]
    )
    episodes: list[EpisodeOutline] = Field(default_factory=list)
