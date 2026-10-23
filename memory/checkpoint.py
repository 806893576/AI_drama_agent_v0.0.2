"""Graph 检查点存储。

检查点只保存“最后一个成功节点之后”的 Graph State。
当真实 LLM 因网络、SSL、超时或服务端波动失败时，下一次用同一 job_id 重试，
即可从这个状态继续，而不是从输入节点重新生成全部产物。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.settings import get_settings


class JsonCheckpointStore:
    def __init__(self, root_dir: str | Path | None = None) -> None:
        self.root_dir = Path(root_dir) if root_dir else get_settings().storage_dir / "checkpoints"

    def save(self, job_id: str, state: dict[str, Any]) -> Path:
        path = self.root_dir / f"{job_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_to_jsonable(state), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, job_id: str) -> dict[str, Any]:
        path = self.root_dir / f"{job_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, job_id: str) -> bool:
        return (self.root_dir / f"{job_id}.json").exists()

    def load_or_none(self, job_id: str) -> dict[str, Any] | None:
        if not self.exists(job_id):
            return None
        return self.load(job_id)


def _to_jsonable(value: Any) -> Any:
    """递归转成可写入 JSON 的结构，避免 checkpoint 依赖 workflow 模块造成循环导入。"""

    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    return value
