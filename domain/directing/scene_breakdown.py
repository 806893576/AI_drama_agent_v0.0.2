"""导演场景拆解模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class SceneBreakdown(BaseModel):
    """场景拆解：扁平轻结构，便于真实 LLM 稳定输出和后续自然语言传递。"""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    episode_id: str
    scene_number: int
    interior_exterior: str
    time: str | None = None
    location: str
    characters: str
    props: str
    costume_makeup: str
    scene_summary: str
    key_actions: str
    dramatic_function: str
    continuity: str

    @model_validator(mode="before")
    @classmethod
    def _coerce_text_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        for key in (
            "characters",
            "props",
            "costume_makeup",
            "scene_summary",
            "key_actions",
            "dramatic_function",
            "continuity",
        ):
            normalized[key] = _to_text(normalized.get(key))
        return normalized


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list | tuple):
        return "；".join(_to_text(item) for item in value if _to_text(item))
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            text = _to_text(item)
            if text:
                parts.append(f"{key}：{text}")
        return "；".join(parts)
    return str(value).strip()
