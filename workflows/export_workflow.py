"""交付物导出工作流。"""

from __future__ import annotations

import json
from pathlib import Path


def export_summary_to_json(summary: dict, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
