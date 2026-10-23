"""存储服务统一入口。"""

from __future__ import annotations

from services.storage.artifact_store import ArtifactStore
from services.storage.asset_store import AssetRegistryStore


class StorageClient:
    def __init__(self) -> None:
        self.artifacts = ArtifactStore()
        self.assets = AssetRegistryStore()
