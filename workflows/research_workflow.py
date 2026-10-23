"""调研工作流。"""

from __future__ import annotations


def build_research_brief(topic: str) -> dict[str, str | list[str]]:
    return {"topic": topic, "notes": ["当前版本不自动联网，保留人工或外部工具补充入口。"]}
