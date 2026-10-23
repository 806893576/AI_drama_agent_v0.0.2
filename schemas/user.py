"""用户 Schema。"""

from __future__ import annotations

from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: str
    display_name: str | None = None
