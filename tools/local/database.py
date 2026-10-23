"""本地数据库工具。"""

from __future__ import annotations

from database.connection import JsonDatabase
from tools.decorator import drama_tool


@drama_tool(name="get_job_record", description="读取任务记录")
def get_job_record(job_id: str) -> dict | None:
    record = JsonDatabase().get_job(job_id)
    return record.model_dump(mode="json") if record else None
