"""镜头意图模型。"""

from __future__ import annotations

from pydantic import BaseModel


class ShotIntent(BaseModel):
    shot_id: str
    intent: str
    information: str
    emotion: str
