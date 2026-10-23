"""分集批处理工具。"""

from __future__ import annotations


def chunk_episode_ids(episode_ids: list[str], batch_size: int = 5) -> list[list[str]]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    return [episode_ids[index : index + batch_size] for index in range(0, len(episode_ids), batch_size)]
