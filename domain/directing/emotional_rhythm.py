"""情绪节奏模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EmotionalRhythm(BaseModel):
    scene_id: str
    start: str
    middle: str
    end: str
    conflict_level: int
    pause_points: list[str] = Field(default_factory=list)
