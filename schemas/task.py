"""任务 Schema。"""

from __future__ import annotations

from pydantic import BaseModel


class TaskRequest(BaseModel):
    job_id: str
    user_request: str
