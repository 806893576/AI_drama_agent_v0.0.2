"""本地计算工具。"""

from __future__ import annotations

from tools.decorator import drama_tool


@drama_tool(name="estimate_runtime", description="估算短剧总时长")
def estimate_runtime(episode_count: int, episode_duration_minutes: float) -> float:
    return round(episode_count * episode_duration_minutes, 2)


@drama_tool(name="estimate_shot_count", description="估算分镜数量")
def estimate_shot_count(scene_count: int, shots_per_scene: int = 2) -> int:
    return scene_count * shots_per_scene
