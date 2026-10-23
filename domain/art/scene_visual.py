"""场景视觉模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SceneVisualSpec(BaseModel):
    scene_id: str
    location_style: str
    color_palette: list[str] = Field(default_factory=list)
    reference_prompt_id: str | None = None
