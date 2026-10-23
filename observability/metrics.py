"""内存指标收集器。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(slots=True)
class MetricsRegistry:
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    gauges: dict[str, float] = field(default_factory=dict)

    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        self.gauges[name] = value

    def snapshot(self) -> dict:
        return {"counters": dict(self.counters), "gauges": dict(self.gauges)}


metrics_registry = MetricsRegistry()
