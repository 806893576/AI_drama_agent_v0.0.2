"""任务工作流辅助函数。"""

from __future__ import annotations

from database.models import JobRecord


def build_job_record(user_request: str, summary: dict) -> JobRecord:
    status = "completed" if summary.get("final_output_ready") else "paused_or_rejected"
    return JobRecord(
        job_id=summary["job_id"],
        user_request=user_request,
        status=status,
        final_message=summary.get("final_message"),
        artifact_ids=summary.get("artifact_ids", {}),
        event_count=summary.get("event_count", 0),
    )
