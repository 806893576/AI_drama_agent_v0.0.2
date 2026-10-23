"""服化道模型。"""

from __future__ import annotations

from pydantic import BaseModel


class CostumePropSpec(BaseModel):
    asset_id: str
    name: str
    continuity_note: str | None = None
