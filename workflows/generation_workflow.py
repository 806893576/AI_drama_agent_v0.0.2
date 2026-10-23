"""短剧生成工作流入口。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from database.connection import JsonDatabase
from graph.builder import build_drama_graph
from graph.execution_options import ExecutionOptions
from memory.checkpoint import JsonCheckpointStore
from services.llm import (
    LLMRuntimeError,
    LLMStructuredOutputError,
    llm_trace_context,
    structured_output_mode,
)
from state.artifact_refs import get_artifact_ref_id
from workflows.task_workflow import build_job_record


@dataclass(slots=True)
class WorkflowRunResult:
    state: dict[str, Any]
    summary: dict[str, Any]


def run_generation(
    user_request: str,
    job_id: str = "job_debug",
    execution_options: ExecutionOptions | dict | None = None,
    llm_format_mode: str = "interrupt",
    resume_from_checkpoint: bool = False,
) -> WorkflowRunResult:
    """执行完整 LangGraph 流程并保存任务摘要。

    execution_options 控制是否跳过部分高成本节点。默认值为完整流程。
    """

    checkpoint = JsonCheckpointStore().load_or_none(job_id) if resume_from_checkpoint else None
    options = _normalize_execution_options(
        execution_options
        if execution_options is not None or checkpoint is None
        else checkpoint.get("execution_options")
    )
    graph = build_drama_graph()
    initial_state = _build_initial_state(
        user_request=user_request,
        job_id=job_id,
        execution_options=options,
        resume_from_checkpoint=resume_from_checkpoint,
        checkpoint=checkpoint,
    )
    try:
        with llm_trace_context(job_id), structured_output_mode(llm_format_mode):
            state = graph.invoke(initial_state)
    except LLMStructuredOutputError as exc:
        state = _build_llm_format_pause_state(
            job_id=job_id,
            user_request=user_request,
            execution_options=options,
            error=exc,
            resume_from_checkpoint=resume_from_checkpoint,
        )
    except LLMRuntimeError as exc:
        state = _build_llm_runtime_pause_state(
            job_id=job_id,
            user_request=user_request,
            execution_options=options,
            error=exc,
            resume_from_checkpoint=resume_from_checkpoint,
        )
    summary = summarize_graph_result(state)
    JsonDatabase().save_job(build_job_record(user_request=user_request, summary=summary))
    return WorkflowRunResult(state=state, summary=summary)


def run_fast_draft_generation(user_request: str, job_id: str = "job_debug") -> WorkflowRunResult:
    """快速草案入口：跳过审核类节点，只生成制作方案和最终交付包。"""

    return run_generation(
        user_request=user_request,
        job_id=job_id,
        execution_options=ExecutionOptions.fast_draft(),
    )


def summarize_graph_result(result: dict[str, Any]) -> dict[str, Any]:
    artifact_refs = result.get("artifact_refs", {})
    events = result.get("events", [])
    return {
        "job_id": result.get("job_id"),
        "current_stage": _to_jsonable(result.get("current_stage")),
        "next_node": _to_jsonable(result.get("next_node")),
        "final_output_ready": result.get("final_output_ready", False),
        "human_confirmation_required": result.get("human_confirmation_required", False),
        "human_confirmation_point": result.get("human_confirmation_point"),
        "terminated": result.get("terminated", False),
        "final_message": result.get("final_message"),
        "human_questions": result.get("human_questions", []),
        "editable_artifact_refs": _to_jsonable(result.get("editable_artifact_refs", {})),
        "resume_target_node": result.get("resume_target_node"),
        "llm_format_error": result.get("llm_format_error"),
        "llm_repair_available": result.get("llm_repair_available", False),
        "llm_runtime_error": result.get("llm_runtime_error"),
        "llm_retry_available": result.get("llm_retry_available", False),
        "resume_from_checkpoint": result.get("resume_from_checkpoint", False),
        "completed_nodes": result.get("completed_nodes", []),
        "last_completed_node": result.get("last_completed_node"),
        "execution_options": _to_jsonable(result.get("execution_options", {})),
        "artifact_ids": {
            key: get_artifact_ref_id(ref)
            for key, ref in artifact_refs.items()
        },
        "event_count": len(events),
        "last_event": _to_jsonable(events[-1]) if events else None,
    }


def to_jsonable(value: Any) -> Any:
    return _to_jsonable(value)


def _normalize_execution_options(raw: ExecutionOptions | dict | None) -> ExecutionOptions:
    if isinstance(raw, ExecutionOptions):
        return raw
    if isinstance(raw, dict):
        return ExecutionOptions(**raw)
    return ExecutionOptions()


def _build_initial_state(
    *,
    user_request: str,
    job_id: str,
    execution_options: ExecutionOptions,
    resume_from_checkpoint: bool,
    checkpoint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if checkpoint is None:
        return {
            "job_id": job_id,
            "user_request": user_request,
            "execution_options": execution_options.model_dump(mode="json"),
            "completed_nodes": [],
            "confirmed_human_points": [],
            "resume_mode": False,
            "resume_from_checkpoint": False,
        }

    # 恢复运行只复用最后成功 state，并用本次请求的执行开关覆盖，方便用户重试时调整审核开关。
    checkpoint["job_id"] = job_id
    checkpoint["user_request"] = checkpoint.get("user_request") or user_request
    checkpoint["execution_options"] = execution_options.model_dump(mode="json")
    checkpoint.setdefault("confirmed_human_points", [])
    checkpoint["resume_mode"] = True
    checkpoint["resume_from_checkpoint"] = True
    checkpoint["final_output_ready"] = False
    checkpoint["human_confirmation_required"] = False
    checkpoint["terminated"] = False
    checkpoint["final_message"] = None
    checkpoint.pop("llm_format_error", None)
    checkpoint.pop("llm_runtime_error", None)
    checkpoint["llm_repair_available"] = False
    checkpoint["llm_retry_available"] = False
    return checkpoint


def _build_llm_format_pause_state(
    *,
    job_id: str,
    user_request: str,
    execution_options: ExecutionOptions,
    error: LLMStructuredOutputError,
    resume_from_checkpoint: bool = False,
) -> dict[str, Any]:
    message = (
        f"LLM 结构化输出失败：{error.prompt_id}。请确认是否将原始输出、错误信息和目标 schema "
        "再次提交给 LLM 自动修复，或退出本次任务。"
    )
    checkpoint = _checkpoint_pause_base(job_id)
    return {
        **checkpoint,
        "job_id": job_id,
        "user_request": checkpoint.get("user_request") or user_request,
        "execution_options": execution_options.model_dump(mode="json"),
        "resume_from_checkpoint": resume_from_checkpoint,
        "resume_mode": False,
        "final_output_ready": False,
        "human_confirmation_required": True,
        "terminated": False,
        "final_message": message,
        "human_questions": [
            "是否确认将原始输出、错误信息和目标 schema 再次提交给 LLM 进行格式修复？",
            "选择退出则不会继续消耗 token。",
        ],
        "artifact_refs": checkpoint.get("artifact_refs", {}),
        "events": checkpoint.get("events", []),
        "llm_format_error": error.to_summary(),
        "llm_repair_available": True,
        "llm_runtime_error": None,
        "llm_retry_available": False,
    }


def _build_llm_runtime_pause_state(
    *,
    job_id: str,
    user_request: str,
    execution_options: ExecutionOptions,
    error: LLMRuntimeError,
    resume_from_checkpoint: bool = False,
) -> dict[str, Any]:
    message = (
        f"LLM 请求失败：{error.prompt_id}。这通常是网络、SSL、超时或模型服务异常。"
        "任务已暂停，未把规则兜底结果写成正式创作产物。"
    )
    checkpoint = _checkpoint_pause_base(job_id)
    return {
        **checkpoint,
        "job_id": job_id,
        "user_request": checkpoint.get("user_request") or user_request,
        "execution_options": execution_options.model_dump(mode="json"),
        "resume_from_checkpoint": resume_from_checkpoint,
        "resume_mode": False,
        "final_output_ready": False,
        "human_confirmation_required": True,
        "terminated": False,
        "final_message": message,
        "human_questions": [
            "请检查网络/API 服务状态后，决定是否用同一任务 ID 重新提交。",
            "重新提交会再次调用真实 LLM；退出则不会继续消耗 token。",
        ],
        "artifact_refs": checkpoint.get("artifact_refs", {}),
        "events": checkpoint.get("events", []),
        "llm_format_error": None,
        "llm_repair_available": False,
        "llm_runtime_error": error.to_summary(),
        "llm_retry_available": True,
    }


def _checkpoint_pause_base(job_id: str) -> dict[str, Any]:
    """暂停响应复用最后成功 checkpoint，让前端能看到已生成 artifact 和完成节点。"""

    return JsonCheckpointStore().load_or_none(job_id) or {
        "artifact_refs": {},
        "events": [],
        "completed_nodes": [],
        "last_completed_node": None,
    }


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value
