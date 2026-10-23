"""资产文件存储服务占位。

用于保存图片、音频、视频、参考图、生成结果和外部资源引用，并与 Asset Registry 建立关联。
"""

# 负责把 Asset Registry 保存为 JSON，并能读取、更新、查询。
from __future__ import annotations

import json
from pathlib import Path

from domain.assets.asset_registry import AssetRegistry


"""
它会保存到：
    storage/assets/job_001/asset_registry.json
后续 Asset Manager 节点可以：
    registry = store.load(job_id)
    registry.upsert_character(...)
    store.save(registry)
"""
class AssetRegistryStore:
    def __init__(self, root_dir: str | Path = "storage/assets") -> None:
        self.root_dir = Path(root_dir)

    def _registry_path(self, job_id: str) -> Path:
        return self.root_dir / job_id / "asset_registry.json"

    def save(self, registry: AssetRegistry) -> Path:
        path = self._registry_path(registry.job_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        if hasattr(registry, "model_dump_json"):
            text = registry.model_dump_json(indent=2)
        else:
            text = registry.json(indent=2)

        path.write_text(text, encoding="utf-8")
        return path

    def load(self, job_id: str) -> AssetRegistry:
        path = self._registry_path(job_id)
        if not path.exists():
            raise FileNotFoundError(f"Asset registry not found: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        return AssetRegistry(**data)

    def exists(self, job_id: str) -> bool:
        return self._registry_path(job_id).exists()