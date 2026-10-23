"""Human confirmation points used by optional workflow interrupts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

HumanConfirmationPoint = Literal["brief", "style", "episode_outline"]

BRIEF_CONFIRMATION_POINT: HumanConfirmationPoint = "brief"
STYLE_CONFIRMATION_POINT: HumanConfirmationPoint = "style"
EPISODE_OUTLINE_CONFIRMATION_POINT: HumanConfirmationPoint = "episode_outline"


class HumanConfirmationRequestState(BaseModel):
    """Serializable state shown to the frontend when a workflow pauses."""

    point: HumanConfirmationPoint
    title: str
    editable_artifact_keys: list[str] = Field(default_factory=list)
    resume_target_node: str | None = None
    questions: list[str] = Field(default_factory=list)
