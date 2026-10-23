"""长期记忆。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.settings import get_settings


class LongTermMemory:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else get_settings().storage_dir / "memory" / "long_memory.json"

    def put(self, key: str, value: Any) -> None:
        data = self._read()
        data[key] = value
        self._write(data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._read().get(key, default)

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
