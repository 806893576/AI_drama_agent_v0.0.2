"""运行配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Drama Agent Platform"
    app_version: str = "0.0.3"
    environment: str = "local"
    storage_dir: Path = Path("storage")
    artifact_dir: Path = Path("storage/artifacts")
    asset_dir: Path = Path("storage/assets")
    database_dir: Path = Path("storage/database")
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """从环境变量加载配置。

    使用标准库实现，避免本项目在早期阶段强依赖 pydantic-settings。
    """

    storage_dir = Path(os.getenv("DRAMA_STORAGE_DIR", "storage"))
    return Settings(
        app_name=os.getenv("DRAMA_APP_NAME", "Drama Agent Platform"),
        app_version=os.getenv("DRAMA_APP_VERSION", "0.0.3"),
        environment=os.getenv("DRAMA_ENV", "local"),
        storage_dir=storage_dir,
        artifact_dir=Path(os.getenv("DRAMA_ARTIFACT_DIR", str(storage_dir / "artifacts"))),
        asset_dir=Path(os.getenv("DRAMA_ASSET_DIR", str(storage_dir / "assets"))),
        database_dir=Path(os.getenv("DRAMA_DATABASE_DIR", str(storage_dir / "database"))),
        log_level=os.getenv("DRAMA_LOG_LEVEL", "INFO"),
    )
