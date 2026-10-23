"""角色视觉模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CharacterVisualSpec(BaseModel):
    character_id: str
    appearance: str
    costume_keywords: list[str] = Field(default_factory=list)
    reference_prompt_id: str | None = None
