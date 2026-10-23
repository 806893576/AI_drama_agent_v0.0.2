"""轻量持久化模型。"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class JobRecord(BaseModel):
    job_id: str
    user_request: str
    status: str
    final_message: str | None = None
    artifact_ids: dict[str, str] = Field(default_factory=dict)
    event_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationRecord(BaseModel):
    evaluation_id: str
    job_id: str
    scores: dict[str, float] = Field(default_factory=dict)
    passed: bool = True
    summary: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
