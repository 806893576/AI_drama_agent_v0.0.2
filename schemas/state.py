"""状态 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class JobStateSummary(BaseModel):
    job_id: str
    current_stage: str | None = None
    final_output_ready: bool = False
    artifact_ids: dict[str, str] = Field(default_factory=dict)
