"""导演分镜设计模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ShotDesign(BaseModel):
    """分镜设计。

    表演调度阶段也复用这个结构，但会把 shot_content 替换为表演增强版完整剧情描述。
    """

    model_config = ConfigDict(extra="forbid")

    shot_id: str
    scene_id: str
    shot_number: int
    shot_size: str
    composition: str
    shot_content: str
    camera_position_movement: str
    duration_seconds: float = Field(gt=0, le=15)
    continuity: str | None = None
