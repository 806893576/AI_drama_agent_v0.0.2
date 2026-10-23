"""表演调度模型。"""

from __future__ import annotations

from pydantic import BaseModel


class PerformanceDirection(BaseModel):
    scene_id: str
    blocking: str
    expression: str
    interaction: str
