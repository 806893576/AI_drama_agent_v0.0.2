"""节点级检查点与恢复包装器。

LangGraph 默认会在一次 invoke 完成后返回最终 state；如果中途节点抛出异常，
调用方拿不到“异常发生前的最新 state”。本模块用一个很薄的节点包装器，在每个
节点成功后主动保存 checkpoint，并在恢复模式下跳过已经成功完成的节点。
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from memory.checkpoint import JsonCheckpointStore
from services.runtime_status import (
    mark_node_completed,
    mark_node_failed,
    mark_node_running,
    mark_node_skipped,
)

NodeFn = Callable[[dict[str, Any]], dict[str, Any]]


def checkpointed_node(node_id: str, node_fn: NodeFn) -> NodeFn:
    """包装一个 LangGraph node，让它支持“成功后落盘、恢复时跳过”。

    关键规则：
    - 普通运行时不跳过任何节点，避免影响审核返工等正常业务回路。
    - 只有 `resume_mode=True` 时，才会根据 `completed_nodes` 跳过已完成节点。
    - 恢复模式下遇到第一个未完成节点并执行成功后，自动关闭恢复模式；后续节点按正常逻辑运行。
    """

    def _wrapped(state: dict[str, Any]) -> dict[str, Any]:
        job_id = str(state.get("job_id", "job_unknown"))
        completed_nodes = list(state.get("completed_nodes", []))
        if state.get("resume_mode") and node_id in completed_nodes:
            # 已成功节点不再重复调用 LLM，也不重复写 artifact，直接沿用 checkpoint 中的结果。
            mark_node_skipped(job_id, node_id, state)
            return {}

        mark_node_running(job_id, node_id, state)
        try:
            update = node_fn(state)
        except BaseException as exc:
            mark_node_failed(job_id, node_id, exc)
            raise
        merged = _merge_state_for_checkpoint(state, update)

        if node_id not in completed_nodes:
            completed_nodes.append(node_id)

        merged["completed_nodes"] = completed_nodes
        merged["last_completed_node"] = node_id
        merged.pop("llm_format_error", None)
        merged.pop("llm_runtime_error", None)
        merged["llm_repair_available"] = False
        merged["llm_retry_available"] = False

        resume_mode_finished = bool(state.get("resume_mode"))
        if resume_mode_finished:
            # 第一个未完成节点已执行成功，说明已经追上失败点，之后恢复为正常执行。
            merged["resume_mode"] = False

        JsonCheckpointStore().save(str(merged.get("job_id", "job_unknown")), merged)
        mark_node_completed(job_id, node_id, merged, update)

        returned_update = dict(update)
        returned_update["completed_nodes"] = completed_nodes
        returned_update["last_completed_node"] = node_id
        returned_update["llm_repair_available"] = False
        returned_update["llm_retry_available"] = False
        if resume_mode_finished:
            returned_update["resume_mode"] = False
        return returned_update

    return _wrapped


def _merge_state_for_checkpoint(state: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """按项目当前 reducer 语义合并 state，生成可落盘的最新快照。"""

    merged = deepcopy(dict(state))
    for key, value in update.items():
        if key == "artifact_refs":
            refs = dict(merged.get("artifact_refs", {}))
            refs.update(value or {})
            merged[key] = refs
        elif key == "events":
            merged[key] = list(merged.get("events", [])) + list(value or [])
        elif key == "retry_counts":
            counts = dict(merged.get("retry_counts", {}))
            for retry_key, retry_value in (value or {}).items():
                counts[retry_key] = counts.get(retry_key, 0) + retry_value
            merged[key] = counts
        else:
            merged[key] = value
    return merged
