"""JSON 文件数据库。

这是本地开发友好的持久化层。接口刻意做薄，后续替换为 PostgreSQL 时，
API 和 workflow 层无需改动太多。
"""

from __future__ import annotations

import json
from pathlib import Path

from core.settings import get_settings
from database.models import EvaluationRecord, JobRecord


class JsonDatabase:
    def __init__(self, root_dir: str | Path | None = None) -> None:
        self.root_dir = Path(root_dir) if root_dir else get_settings().database_dir

    def _jobs_path(self) -> Path:
        return self.root_dir / "jobs.json"

    def _evaluations_path(self) -> Path:
        return self.root_dir / "evaluations.json"

    def save_job(self, record: JobRecord) -> None:
        data = self._read_map(self._jobs_path())
        data[record.job_id] = record.model_dump(mode="json")
        self._write_map(self._jobs_path(), data)

    def get_job(self, job_id: str) -> JobRecord | None:
        data = self._read_map(self._jobs_path()).get(job_id)
        return JobRecord(**data) if data else None

    def list_jobs(self) -> list[JobRecord]:
        return [JobRecord(**item) for item in self._read_map(self._jobs_path()).values()]

    def save_evaluation(self, record: EvaluationRecord) -> None:
        data = self._read_map(self._evaluations_path())
        data[record.evaluation_id] = record.model_dump(mode="json")
        self._write_map(self._evaluations_path(), data)

    def _read_map(self, path: Path) -> dict:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_map(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
