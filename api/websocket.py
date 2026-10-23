"""WebSocket 事件流工具。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class EventStreamHub:
    """轻量事件流中心。

    当前用于内存内广播，后续生产部署可替换为 Redis Pub/Sub 或消息队列。
    """

    def __init__(self) -> None:
        self._events: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def publish(self, job_id: str, event: dict[str, Any]) -> None:
        self._events[job_id].append(event)

    def list_events(self, job_id: str) -> list[dict[str, Any]]:
        return list(self._events.get(job_id, []))


event_stream_hub = EventStreamHub()
