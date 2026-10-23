"""LLM 调用追踪落盘工具。"""

from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.settings import get_settings

_llm_trace_job_id: ContextVar[str] = ContextVar("llm_trace_job_id", default="job_unknown")


@contextmanager
def llm_trace_context(job_id: str):
    """设置当前 LLM trace 归属的任务 ID。"""

    token = _llm_trace_job_id.set(job_id or "job_unknown")
    try:
        yield
    finally:
        _llm_trace_job_id.reset(token)


class LLMTraceStore:
    """把每次 LLM 调用/解析结果写入 JSON 文件。"""

    def __init__(self, root_dir: str | Path | None = None) -> None:
        self.root_dir = Path(root_dir) if root_dir else get_settings().storage_dir / "llm_traces"

    def save(self, payload: dict[str, Any]) -> Path:
        job_id = str(payload.get("job_id") or current_llm_trace_job_id())
        trace_id = str(payload.get("trace_id") or _new_trace_id(payload.get("prompt_id")))
        trace_dir = self.root_dir / _safe_path_part(job_id)
        trace_dir.mkdir(parents=True, exist_ok=True)

        data = {
            **_to_jsonable(payload),
            "trace_id": trace_id,
            "job_id": job_id,
            "created_at": datetime.now(UTC).isoformat(),
        }
        path = trace_dir / f"{trace_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_prompt(self, payload: dict[str, Any]) -> Path:
        """把发送给 LLM 前的完整 system/user prompt 单独落盘。"""

        job_id = str(payload.get("job_id") or current_llm_trace_job_id())
        trace_id = str(payload.get("trace_id") or _new_trace_id(payload.get("prompt_id")))
        prompt_dir = self.root_dir / _safe_path_part(job_id) / "prompts"
        prompt_dir.mkdir(parents=True, exist_ok=True)

        data = {
            **_to_jsonable(payload),
            "trace_id": trace_id,
            "job_id": job_id,
            "created_at": datetime.now(UTC).isoformat(),
        }
        path = prompt_dir / f"{trace_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def list_prompts(self, job_id: str) -> list[dict[str, Any]]:
        prompt_dir = self.root_dir / _safe_path_part(job_id) / "prompts"
        if not prompt_dir.exists():
            return []

        prompts: list[dict[str, Any]] = []
        for path in sorted(prompt_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            messages = data.get("messages", [])
            prompts.append(
                {
                    "trace_id": data.get("trace_id") or path.stem,
                    "job_id": data.get("job_id") or job_id,
                    "created_at": data.get("created_at"),
                    "prompt_id": data.get("prompt_id"),
                    "prompt_version": data.get("prompt_version"),
                    "path": str(path),
                    "message_count": len(messages),
                    "message_summary": summarize_messages(messages),
                }
            )
        return prompts

    def load_prompt(self, job_id: str, trace_id: str) -> dict[str, Any] | None:
        path = (
            self.root_dir
            / _safe_path_part(job_id)
            / "prompts"
            / f"{_safe_path_part(trace_id)}.json"
        )
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        data["path"] = str(path)
        return data


def current_llm_trace_job_id() -> str:
    return _llm_trace_job_id.get()


def llm_trace_enabled() -> bool:
    return os.getenv("LLM_TRACE_ENABLED", "true").lower() not in {"0", "false", "no", "off"}


def new_llm_trace_id(prompt_id: Any) -> str:
    return _new_trace_id(prompt_id)


def summarize_variables(variables: dict[str, Any]) -> dict[str, Any]:
    return {key: _summarize_value(value) for key, value in variables.items()}


def summarize_messages(messages: list[Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for message in messages:
        if isinstance(message, dict):
            role = message.get("role")
            content = message.get("content", "")
        else:
            role = getattr(message, "role", None)
            content = getattr(message, "content", "")
        summaries.append(
            {
                "role": role,
                "char_count": len(str(content)),
                "preview": _truncate(str(content), 500),
            }
        )
    return summaries


def _summarize_value(value: Any, *, depth: int = 0) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")

    if isinstance(value, str):
        return {
            "type": "str",
            "char_count": len(value),
            "preview": _truncate(value, 500),
        }
    if isinstance(value, dict):
        if depth >= 2:
            return {"type": "dict", "keys": list(value.keys()), "size": len(value)}
        return {
            "type": "dict",
            "keys": list(value.keys()),
            "size": len(value),
            "items": {
                key: _summarize_value(item, depth=depth + 1)
                for key, item in list(value.items())[:20]
            },
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "size": len(value),
            "items": [_summarize_value(item, depth=depth + 1) for item in value[:5]],
        }
    return {"type": type(value).__name__, "value": _to_jsonable(value)}


def _to_jsonable(value: Any) -> Any:
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


def _new_trace_id(prompt_id: Any) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    prompt_part = _safe_path_part(str(prompt_id or "unknown"))
    return f"{timestamp}_{prompt_part}_{uuid4().hex[:8]}"


def _safe_path_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "unknown"


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"
