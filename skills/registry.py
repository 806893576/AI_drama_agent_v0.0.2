"""技能注册中心。"""

from __future__ import annotations


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, str] = {}

    def register(self, name: str, description: str) -> None:
        self._skills[name] = description

    def list(self) -> dict[str, str]:
        return dict(self._skills)
