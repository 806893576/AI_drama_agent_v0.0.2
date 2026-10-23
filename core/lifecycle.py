"""应用生命周期。"""

from __future__ import annotations

from core.settings import get_settings
from observability.logger import configure_logging, get_logger


def startup() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    for path in (settings.storage_dir, settings.artifact_dir, settings.asset_dir, settings.database_dir):
        path.mkdir(parents=True, exist_ok=True)
    get_logger(__name__).info("Drama Agent Platform started")


def shutdown() -> None:
    get_logger(__name__).info("Drama Agent Platform stopped")
