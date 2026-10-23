"""Episode Script / 分集剧本模型。

分集剧本只保留四层轻结构：
项目元数据、单集框架、场景切片，以及场景内完整正文剧本。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProjectMetadata(BaseModel):
    """项目元数据层。"""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    genre: str | None = None
    total_episodes: int | None = None
    platform: str | None = None
    episode_duration_minutes: float | None = None


class EpisodeCharacter(BaseModel):
    """本集出场人物的轻量说明。"""

    model_config = ConfigDict(extra="forbid")

    name: str
    brief: str | None = None


class EpisodeLevel(BaseModel):
    """单集框架层。"""

    model_config = ConfigDict(extra="forbid")

    episode_number: int
    episode_title: str | None = None
    core_function: str
    appearing_characters: list[EpisodeCharacter] = Field(default_factory=list)
    ending_hook: str | None = None


class SceneScript(BaseModel):
    """场景切片层。

    `script_text` 是该场景完整正文剧本，可包含动作、对白、短信/屏幕信息和转场。
    `continuity` 用于表达“紧接上一场”“同一时间”等承接关系。
    """

    model_config = ConfigDict(extra="forbid")

    scene_number: int
    interior_exterior: str
    location: str
    time: str | None = None
    continuity: str | None = None
    script_text: str


class EpisodeScript(BaseModel):
    """单集剧本。"""

    model_config = ConfigDict(extra="forbid")

    episode_script_id: str
    artifact_type: str = "episode_script"
    version: int = 1
    project_metadata: ProjectMetadata = Field(default_factory=ProjectMetadata)
    episode: EpisodeLevel
    scenes: list[SceneScript] = Field(default_factory=list)
