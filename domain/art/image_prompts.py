"""美术组图像提示词模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CharacterAssetPrompt(BaseModel):
    """角色设定图或同一角色的造型变体图。"""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    character_name: str
    variant: str
    base_asset_id: str | None = None
    used_in_scene_ids: list[str] = Field(default_factory=list)
    used_in_shot_ids: list[str] = Field(default_factory=list)
    prompt: str
    negative_prompt: str | None = None
    style_keywords: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)


class SceneAssetPrompt(BaseModel):
    """场景图提示词，并记录哪些镜头复用同一场景资产。"""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    scene_name: str
    scene_id: str
    used_in_shot_ids: list[str] = Field(default_factory=list)
    prompt: str
    negative_prompt: str | None = None
    style_keywords: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)


class PropAssetPrompt(BaseModel):
    """关键道具图提示词。"""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    prop_name: str
    used_in_scene_ids: list[str] = Field(default_factory=list)
    used_in_shot_ids: list[str] = Field(default_factory=list)
    prompt: str
    negative_prompt: str | None = None
    style_keywords: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)


class ArtAssetPromptLibrary(BaseModel):
    """第一部分：角色、场景、关键道具的文生图提示词库。"""

    model_config = ConfigDict(extra="forbid")

    character_assets: list[CharacterAssetPrompt] = Field(default_factory=list)
    scene_assets: list[SceneAssetPrompt] = Field(default_factory=list)
    prop_assets: list[PropAssetPrompt] = Field(default_factory=list)


class ShotPromptPlan(BaseModel):
    """第二部分：每个分镜的资产引用和分镜参考图提示词。"""

    model_config = ConfigDict(extra="forbid")

    shot_id: str
    scene_id: str
    scene_asset_id: str
    character_asset_ids: list[str] = Field(default_factory=list)
    prop_asset_ids: list[str] = Field(default_factory=list)
    shot_reference_prompt: str
    negative_prompt: str | None = None
    continuity_notes: str | None = None
    video_prompt_source_notes: str | None = None


class ArtPromptPackage(BaseModel):
    """美术组输出包：资产提示词库 + 分镜引用计划。"""

    model_config = ConfigDict(extra="forbid")

    art_prompt_package_id: str
    style_profile: str
    asset_prompts: ArtAssetPromptLibrary = Field(default_factory=ArtAssetPromptLibrary)
    shot_prompt_plan: list[ShotPromptPlan] = Field(default_factory=list)
