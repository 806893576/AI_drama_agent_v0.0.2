"""技能加载器。"""

from __future__ import annotations

from pathlib import Path


def load_skill_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
