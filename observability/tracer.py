"""链路追踪工具。"""

from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

from observability.logger import get_logger
from observability.metrics import metrics_registry


@contextmanager
def trace_span(name: str) -> Iterator[None]:
    start = perf_counter()
    get_logger(__name__).debug("span started: %s", name)
    try:
        yield
        metrics_registry.increment(f"{name}.success")
    except Exception:
        metrics_registry.increment(f"{name}.error")
        raise
    finally:
        metrics_registry.set_gauge(f"{name}.last_duration_ms", (perf_counter() - start) * 1000)
        get_logger(__name__).debug("span finished: %s", name)
