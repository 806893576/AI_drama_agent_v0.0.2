"""进程内任务运行状态。

用于本地前端轮询展示“当前正在运行的节点”。这是实时 UI 辅助状态，不替代
checkpoint、artifact 或数据库中的持久化结果。
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from threading import Lock
from typing import Any

_LOCK = Lock()
_JOB_STATUS: dict[str, dict[str, Any]] = {}


def mark_node_running(job_id: str, node_id: str, state: dict[str, Any]) -> None:
    now = _now()
    with _LOCK:
        current = _JOB_STATUS.get(job_id, {})
        _JOB_STATUS[job_id] = {
            **current,
            "job_id": job_id,
            "status": "running",
            "current_node": node_id,
            "current_stage": _to_text(state.get("current_stage")),
            "started_at": current.get("started_at") or now,
            "updated_at": now,
            "completed_nodes": list(state.get("completed_nodes", [])),
            "last_completed_node": state.get("last_completed_node"),
            "message": f"正在运行节点：{node_id}",
            "artifact_ids": _artifact_ids(state.get("artifact_refs", {})),
        }


def mark_node_completed(
    job_id: str,
    node_id: str,
    merged_state: dict[str, Any],
    update: dict[str, Any],
) -> None:
    now = _now()
    with _LOCK:
        current = _JOB_STATUS.get(job_id, {})
        _JOB_STATUS[job_id] = {
            **current,
            "job_id": job_id,
            "status": "completed_node",
            "current_node": None,
            "current_stage": _to_text(merged_state.get("current_stage")),
            "updated_at": now,
            "completed_nodes": list(merged_state.get("completed_nodes", [])),
            "last_completed_node": node_id,
            "message": _latest_event_message(update) or f"节点完成：{node_id}",
            "artifact_ids": _artifact_ids(merged_state.get("artifact_refs", {})),
        }


def mark_node_skipped(job_id: str, node_id: str, state: dict[str, Any]) -> None:
    now = _now()
    with _LOCK:
        current = _JOB_STATUS.get(job_id, {})
        _JOB_STATUS[job_id] = {
            **current,
            "job_id": job_id,
            "status": "skipped",
            "current_node": None,
            "current_stage": _to_text(state.get("current_stage")),
            "updated_at": now,
            "completed_nodes": list(state.get("completed_nodes", [])),
            "last_completed_node": state.get("last_completed_node"),
            "message": f"恢复模式跳过已完成节点：{node_id}",
            "artifact_ids": _artifact_ids(state.get("artifact_refs", {})),
        }


def mark_node_failed(job_id: str, node_id: str, error: BaseException) -> None:
    now = _now()
    with _LOCK:
        current = _JOB_STATUS.get(job_id, {})
        _JOB_STATUS[job_id] = {
            **current,
            "job_id": job_id,
            "status": "failed",
            "current_node": node_id,
            "updated_at": now,
            "message": f"节点失败：{node_id}",
            "error_type": type(error).__name__,
            "error_message": str(error),
        }


def get_job_runtime_status(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        status = _JOB_STATUS.get(job_id)
        return deepcopy(status) if status is not None else None


def _artifact_ids(refs: Any) -> dict[str, str]:
    if not isinstance(refs, dict):
        return {}
    ids: dict[str, str] = {}
    for key, ref in refs.items():
        if hasattr(ref, "artifact_id"):
            ids[key] = str(ref.artifact_id)
        elif isinstance(ref, dict) and "artifact_id" in ref:
            ids[key] = str(ref["artifact_id"])
    return ids


def _latest_event_message(update: dict[str, Any]) -> str | None:
    events = update.get("events") if isinstance(update, dict) else None
    if not events:
        return None
    event = events[-1]
    if hasattr(event, "message"):
        return str(event.message)
    if isinstance(event, dict):
        return event.get("message")
    return None


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _now() -> str:
    return datetime.now(UTC).isoformat()
