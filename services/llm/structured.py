"""结构化 LLM 调用工具。"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, TypeVar

from pydantic import TypeAdapter
from pydantic_core import ValidationError

from prompts import PromptRegistry
from services.llm.client import (
    LLMClient,
    create_llm_client,
    parse_json_response,
    resolve_llm_client_kind,
)
from services.llm.models import LLMMessage, LLMRequest, LLMResponse
from services.llm.trace import (
    LLMTraceStore,
    current_llm_trace_job_id,
    llm_trace_enabled,
    new_llm_trace_id,
    summarize_messages,
    summarize_variables,
)

T = TypeVar("T")
_structured_output_mode: ContextVar[str] = ContextVar("structured_output_mode", default="interrupt")


class LLMStructuredOutputError(RuntimeError):
    """LLM 输出无法解析或无法通过 Pydantic 校验时抛出的可交互错误。"""

    def __init__(
        self,
        *,
        prompt_id: str,
        raw_output: str,
        error_message: str,
        target_schema: dict[str, Any],
        prompt_version: int | str | None = None,
    ) -> None:
        super().__init__(f"{prompt_id} structured output failed: {error_message}")
        self.prompt_id = prompt_id
        self.prompt_version = prompt_version
        self.raw_output = raw_output
        self.error_message = error_message
        self.target_schema = target_schema

    def to_summary(self, *, raw_limit: int = 4000) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version,
            "error_message": self.error_message,
            "raw_output": _truncate(self.raw_output, raw_limit),
            "target_schema": self.target_schema,
        }


class LLMRuntimeError(RuntimeError):
    """LLM 请求阶段失败时抛出的可见错误。

    这类错误通常来自网络、SSL、超时或服务端异常。真实 LLM 开启时不应静默兜底，
    否则容易把规则模板当作正式创作产物写入 Artifact Store。
    """

    def __init__(
        self,
        *,
        prompt_id: str,
        error_message: str,
        prompt_version: int | str | None = None,
    ) -> None:
        super().__init__(f"{prompt_id} runtime failed: {error_message}")
        self.prompt_id = prompt_id
        self.prompt_version = prompt_version
        self.error_message = error_message

    def to_summary(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version,
            "error_message": self.error_message,
        }


@contextmanager
def structured_output_mode(mode: str):
    """设置结构化输出失败策略。

    - interrupt：解析/校验失败时抛出 LLMStructuredOutputError，由 API/前端请求用户确认。
    - auto_repair：解析/校验失败时，自动把原始输出、错误和 schema 发给 LLM 修复一次。
    """

    token = _structured_output_mode.set(mode)
    try:
        yield
    finally:
        _structured_output_mode.reset(token)


class StructuredLLMRunner:
    """把 Prompt 模板、LLM 调用和 Pydantic 解析封装到一起。"""

    def __init__(
        self,
        client: LLMClient | None = None,
        prompt_registry: PromptRegistry | None = None,
        trace_store: LLMTraceStore | None = None,
    ) -> None:
        self.client = client or create_llm_client()
        self.prompt_registry = prompt_registry or PromptRegistry()
        self.trace_store = trace_store or LLMTraceStore()

    def generate_json(
        self,
        prompt_id: str,
        variables: dict[str, Any],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> tuple[dict[str, Any] | list[Any], LLMResponse]:
        template = self.prompt_registry.get(prompt_id)
        response: LLMResponse | None = None
        trace_id: str | None = None
        prompt_trace_path: Path | None = None
        try:
            request, trace_id, prompt_trace_path = self._build_request(
                template=template,
                prompt_id=prompt_id,
                variables=variables,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response = self.client.generate_sync(request)
            parsed = parse_json_response(response)
            self._save_trace(
                prompt_id=prompt_id,
                prompt_version=template.version,
                trace_id=trace_id,
                prompt_trace_path=prompt_trace_path,
                variables=variables,
                response=response,
                parsed_result=parsed,
                status="success",
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return parsed, response
        except Exception as exc:
            self._save_trace(
                prompt_id=prompt_id,
                prompt_version=template.version,
                trace_id=trace_id,
                prompt_trace_path=prompt_trace_path,
                variables=variables,
                response=response,
                status="error",
                error=exc,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raise

    def generate_model(
        self,
        prompt_id: str,
        variables: dict[str, Any],
        model_type: type[T],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> tuple[T, LLMResponse]:
        template = self.prompt_registry.get(prompt_id)
        schema = TypeAdapter(model_type).json_schema()
        response: LLMResponse | None = None
        trace_id: str | None = None
        prompt_trace_path: Path | None = None

        try:
            request, trace_id, prompt_trace_path = self._build_request(
                template=template,
                prompt_id=prompt_id,
                variables=variables,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response = self.client.generate_sync(request)
            data = parse_json_response(response)
            parsed = TypeAdapter(model_type).validate_python(data)
            self._save_trace(
                prompt_id=prompt_id,
                prompt_version=template.version,
                trace_id=trace_id,
                prompt_trace_path=prompt_trace_path,
                variables=variables,
                response=response,
                parsed_result=parsed,
                status="success",
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return parsed, response
        except (ValueError, ValidationError) as exc:
            raw_output = response.content if response is not None else ""
            self._save_trace(
                prompt_id=prompt_id,
                prompt_version=template.version,
                trace_id=trace_id,
                prompt_trace_path=prompt_trace_path,
                variables=variables,
                response=response,
                status="structured_output_error",
                error=exc,
                target_schema=schema,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if _structured_output_mode.get() == "auto_repair":
                (
                    repaired_response,
                    repair_trace_id,
                    repair_prompt_trace_path,
                ) = self._repair_structured_output(
                    prompt_id=prompt_id,
                    raw_output=raw_output,
                    error_message=str(exc),
                    target_schema=schema,
                    model=model,
                    temperature=0.0,
                )
                try:
                    repaired_data = parse_json_response(repaired_response)
                    parsed = TypeAdapter(model_type).validate_python(repaired_data)
                    self._save_trace(
                        prompt_id=f"{prompt_id}.format_repair",
                        prompt_version=template.version,
                        trace_id=repair_trace_id,
                        prompt_trace_path=repair_prompt_trace_path,
                        variables={
                            "prompt_id": prompt_id,
                            "error_message": str(exc),
                            "target_schema": schema,
                            "raw_output": raw_output,
                        },
                        response=repaired_response,
                        parsed_result=parsed,
                        status="success",
                        model=model,
                        temperature=0.0,
                    )
                    return parsed, repaired_response
                except (ValueError, ValidationError) as repair_exc:
                    self._save_trace(
                        prompt_id=f"{prompt_id}.format_repair",
                        prompt_version=template.version,
                        trace_id=repair_trace_id,
                        prompt_trace_path=repair_prompt_trace_path,
                        variables={
                            "prompt_id": prompt_id,
                            "error_message": str(exc),
                            "target_schema": schema,
                            "raw_output": raw_output,
                        },
                        response=repaired_response,
                        status="structured_output_error",
                        error=repair_exc,
                        target_schema=schema,
                        model=model,
                        temperature=0.0,
                    )
                    raise LLMStructuredOutputError(
                        prompt_id=prompt_id,
                        prompt_version=template.version,
                        raw_output=repaired_response.content,
                        error_message=f"Auto repair failed. original={exc}; repair={repair_exc}",
                        target_schema=schema,
                    ) from repair_exc

            raise LLMStructuredOutputError(
                prompt_id=prompt_id,
                prompt_version=template.version,
                raw_output=raw_output,
                error_message=str(exc),
                target_schema=schema,
            ) from exc
        except LLMStructuredOutputError:
            raise
        except Exception as exc:
            self._save_trace(
                prompt_id=prompt_id,
                prompt_version=template.version,
                trace_id=trace_id,
                prompt_trace_path=prompt_trace_path,
                variables=variables,
                response=response,
                status="runtime_error",
                error=exc,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raise LLMRuntimeError(
                prompt_id=prompt_id,
                prompt_version=template.version,
                error_message=str(exc),
            ) from exc

    def _build_request(
        self,
        *,
        template: Any,
        prompt_id: str,
        variables: dict[str, Any],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> tuple[LLMRequest, str | None, Path | None]:
        rendered = self.prompt_registry.loader.render(template, variables)
        messages = [
            LLMMessage(role="system", content=rendered["system"]),
            LLMMessage(role="user", content=rendered["user"]),
        ]
        trace_id, prompt_trace_path = self._save_prompt_trace(
            prompt_id=prompt_id,
            prompt_version=template.version,
            variables=variables,
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=_response_format_for(template.output_format),
        )

        request = LLMRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=_response_format_for(template.output_format),
            metadata={
                "prompt_id": prompt_id,
                "prompt_version": template.version,
                "trace_id": trace_id,
                "prompt_trace_path": str(prompt_trace_path) if prompt_trace_path else None,
            },
        )
        return request, trace_id, prompt_trace_path

    def _save_prompt_trace(
        self,
        *,
        prompt_id: str,
        prompt_version: int | str | None,
        variables: dict[str, Any],
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> tuple[str | None, Path | None]:
        if not llm_trace_enabled():
            return None, None

        trace_id = new_llm_trace_id(prompt_id)
        payload = {
            "trace_id": trace_id,
            "job_id": current_llm_trace_job_id(),
            "prompt_id": prompt_id,
            "prompt_version": prompt_version,
            "model_requested": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": response_format,
            "variables_summary": summarize_variables(variables),
            "message_summary": summarize_messages(messages),
            "messages": [_to_jsonable(message) for message in messages],
        }

        try:
            return trace_id, self.trace_store.save_prompt(payload)
        except Exception:
            return trace_id, None

    def _save_trace(
        self,
        *,
        prompt_id: str,
        prompt_version: int | str | None,
        trace_id: str | None,
        prompt_trace_path: Path | None,
        variables: dict[str, Any],
        response: LLMResponse | None,
        status: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        parsed_result: Any = None,
        error: BaseException | None = None,
        target_schema: dict[str, Any] | None = None,
    ) -> None:
        if not llm_trace_enabled():
            return

        payload: dict[str, Any] = {
            "trace_id": trace_id,
            "job_id": current_llm_trace_job_id(),
            "prompt_id": prompt_id,
            "prompt_version": prompt_version,
            "status": status,
            "model_requested": model,
            "model_returned": response.model if response is not None else None,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "variables_summary": summarize_variables(variables),
            "prompt_trace_path": str(prompt_trace_path) if prompt_trace_path else None,
            "raw_output": response.content if response is not None else None,
            "usage": response.usage if response is not None else {},
            "parsed_result": _to_jsonable(parsed_result) if parsed_result is not None else None,
        }
        if target_schema is not None:
            payload["target_schema"] = target_schema
        if error is not None:
            payload["error_type"] = type(error).__name__
            payload["error_message"] = str(error)

        try:
            template = self.prompt_registry.get(prompt_id.removesuffix(".format_repair"))
            rendered = self.prompt_registry.loader.render(template, variables)
            messages = [
                LLMMessage(role="system", content=rendered["system"]),
                LLMMessage(role="user", content=rendered["user"]),
            ]
            payload["message_summary"] = summarize_messages(messages)
        except Exception:
            payload["message_summary"] = []

        try:
            self.trace_store.save(payload)
        except Exception:
            # Trace 不能影响正式 LLM 生成链路。
            return

    def _repair_structured_output(
        self,
        *,
        prompt_id: str,
        raw_output: str,
        error_message: str,
        target_schema: dict[str, Any],
        model: str | None = None,
        temperature: float = 0.0,
    ) -> tuple[LLMResponse, str | None, Path | None]:
        """调用 LLM 只做 JSON 修复，不做内容重写。"""

        repair_prompt_id = f"{prompt_id}.format_repair"
        repair_variables = {
            "prompt_id": prompt_id,
            "error_message": error_message,
            "target_schema": target_schema,
            "raw_output": raw_output,
        }
        messages = [
            LLMMessage(
                role="system",
                content=(
                    "你是严格的 JSON 格式修复器。只根据目标 JSON Schema 修复格式和字段，"
                    "尽量保留原始输出中的创意内容。只输出合法 JSON，不要输出 Markdown。"
                ),
            ),
            LLMMessage(
                role="user",
                content=json.dumps(repair_variables, ensure_ascii=False, indent=2),
            ),
        ]
        response_format = {"type": "json_object"} if _schema_is_object(target_schema) else None
        trace_id, prompt_trace_path = self._save_prompt_trace(
            prompt_id=repair_prompt_id,
            prompt_version=None,
            variables=repair_variables,
            messages=messages,
            model=model,
            temperature=temperature,
            response_format=response_format,
        )
        response = self.client.generate_sync(
            LLMRequest(
                messages=messages,
                model=model,
                temperature=temperature,
                response_format=response_format,
                metadata={
                    "prompt_id": repair_prompt_id,
                    "trace_id": trace_id,
                    "prompt_trace_path": str(prompt_trace_path) if prompt_trace_path else None,
                },
            )
        )
        return response, trace_id, prompt_trace_path


def json_dumps_for_prompt(value: Any) -> str:
    """把 Pydantic 或普通对象转成适合放入 Prompt 的 JSON 字符串。"""

    return json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2)


def llm_enabled() -> bool:
    """集中判断是否启用真实 LLM，避免每个节点重复读取环境变量。"""

    return resolve_llm_client_kind() != "fake"


def generate_model_with_fallback(
    prompt_id: str,
    variables: dict[str, Any],
    model_type: Any,
    fallback,
    *,
    temperature: float = 0.5,
):
    """真实 LLM 优先、规则结果兜底。

    节点只关心“我要哪个结构化模型”，不关心 HTTP、JSON 解析和异常处理细节。
    """

    if not llm_enabled():
        return fallback()

    try:
        parsed, _response = StructuredLLMRunner().generate_model(
            prompt_id,
            variables,
            model_type,
            temperature=temperature,
        )
        return parsed
    except LLMStructuredOutputError:
        raise
    except LLMRuntimeError:
        raise
    except Exception:
        return fallback()


def _to_jsonable(value: Any) -> Any:
    """递归转换为 JSON 可序列化结构，避免模型列表写入 Prompt 时失败。"""

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def _response_format_for(output_format: str) -> dict[str, Any] | None:
    """按需启用 OpenAI JSON object 模式。

    默认关闭，因为部分节点需要模型输出 JSON 数组，而 json_object 模式只适合对象。
    """

    if output_format == "json" and os.getenv("LLM_FORCE_JSON_OBJECT", "false").lower() == "true":
        return {"type": "json_object"}
    return None


def _schema_is_object(schema: dict[str, Any]) -> bool:
    return schema.get("type") == "object" or "properties" in schema


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"
