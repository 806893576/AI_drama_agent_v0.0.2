"""通用 Artifact API Schema。"""

from __future__ import annotations

from pydantic import BaseModel


class ArtifactSummary(BaseModel):
    artifact_id: str
    artifact_type: str
    version: int
    summary: str | None = None
