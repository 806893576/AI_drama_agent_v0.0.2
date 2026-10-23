"""短期记忆。"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ShortTermMemory:
    max_items: int = 20
    _items: deque[dict[str, Any]] = field(default_factory=deque)

    def add(self, item: dict[str, Any]) -> None:
        self._items.append(item)
        while len(self._items) > self.max_items:
            self._items.popleft()

    def list(self) -> list[dict[str, Any]]:
        return list(self._items)
