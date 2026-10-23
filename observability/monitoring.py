"""运行监控与健康检查。"""

from __future__ import annotations

from core.settings import get_settings
from observability.metrics import metrics_registry


def health_snapshot() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.environment,
        "storage_dir": str(settings.storage_dir),
        "metrics": metrics_registry.snapshot(),
    }
