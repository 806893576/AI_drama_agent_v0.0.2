"""功能：LLM 统一接口，负责聊天补全、结构化输出、流式生成和重试策略。"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

from services.llm.models import LLMRequest, LLMResponse


def load_env_file(path: str = ".env") -> None:
    """加载本地 .env 文件。

    只使用标准库，避免为了本地开发额外引入 python-dotenv。
    已存在的环境变量优先级更高，不会被 .env 覆盖。
    """

    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


"""
后续 Agent 只依赖：
    LLMClient.generate()
不关心底层是 OpenAI、Azure、DeepSeek、Qwen、本地模型还是测试假模型。
"""
class LLMClient(ABC):
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from an LLM."""

    def generate_sync(self, request: LLMRequest) -> LLMResponse:
        """同步调用包装，方便 LangGraph 同步节点中直接使用。"""

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.generate(request))
        result: LLMResponse | None = None
        error: BaseException | None = None

        def _runner() -> None:
            nonlocal result, error
            try:
                result = asyncio.run(self.generate(request))
            except BaseException as exc:  # pragma: no cover
                error = exc

        # 异步宿主线程已有事件循环时，用独立线程运行一次性事件循环。
        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()

        if error is not None:
            raise error
        if result is None:
            raise RuntimeError("LLM request finished without a response")
        return result


"""
后续单元测试不用真实 API Key：
    client = FakeLLMClient(response_content='{"title": "测试短剧"}')
    response = await client.generate(request)
"""
class FakeLLMClient(LLMClient):
    """Deterministic test client that does not call external APIs."""

    def __init__(self, response_content: str = "fake response") -> None:
        self.response_content = response_content
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            content=self.response_content,
            model=request.model or "fake-model",
            usage={"prompt_tokens": 0, "completion_tokens": 0},
            raw={},
        )


# 实现结构化 JSON 解析辅助函数
def parse_json_response(response: LLMResponse) -> Any:
    """Parse LLM response content as JSON.

    先尝试直接解析；失败后再提取 Markdown fenced code 或正文中的第一个 JSON 块。
    这样可以提高模型“内容正确但外面包了说明文字”时的解析成功率。
    """

    try:
        return json.loads(response.content)
    except json.JSONDecodeError as exc:
        extracted = extract_json_text(response.content)
        if extracted != response.content:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass
        raise ValueError("LLM response content is not valid JSON") from exc


def extract_json_text(content: str) -> str:
    """从模型输出中提取最可能的 JSON 文本。"""

    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    if text.startswith("{") or text.startswith("["):
        return text

    object_start = text.find("{")
    array_start = text.find("[")
    candidates = [index for index in (object_start, array_start) if index >= 0]
    if not candidates:
        return content

    start = min(candidates)
    opening = text[start]
    closing = "}" if opening == "{" else "]"
    end = text.rfind(closing)
    if end <= start:
        return content
    return text[start : end + 1].strip()


# 如果你想直接解析成 Pydantic 模型，可以追加：
"""
后续 Agent 会要求模型输出 JSON，然后解析成：
    CreativeBrief
    ScriptReviewReport
    RepairPlan
例如：
    brief = parse_model_response(response, CreativeBrief)
"""
def parse_model_response(response: LLMResponse, model_type: type[BaseModel]) -> BaseModel:
    """Parse LLM response content into a Pydantic model."""
    data = parse_json_response(response)

    if hasattr(model_type, "model_validate"):
        return model_type.model_validate(data)

    return model_type.parse_obj(data)


"""
后续只要配置：
    OPENAI_API_KEY=...
    OPENAI_BASE_URL=...
    OPENAI_MODEL=...
    就可以用统一 Client 调模型。
注意：这一步只是基础兼容实现，不处理流式输出、工具调用、多模态、重试。这些后续再加。
"""
class OpenAICompatibleLLMClient(LLMClient):
    """Minimal OpenAI-compatible chat completions client.

    Works with APIs that follow:
    POST /v1/chat/completions
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: float = 60.0,
        max_retries: int | None = None,
        retry_base_delay: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        load_env_file()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com").rstrip("/")
        self.default_model = default_model or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
        self.timeout = timeout
        self.max_retries = (
            max_retries if max_retries is not None else _env_int("LLM_MAX_RETRIES", 2)
        )
        self.retry_base_delay = (
            retry_base_delay
            if retry_base_delay is not None
            else _env_float("LLM_RETRY_BASE_DELAY", 0.5)
        )
        self.transport = transport

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        for attempt in range(self.max_retries + 1):
            try:
                return await self._generate_once(request)
            except Exception as exc:
                if attempt >= self.max_retries or not _is_retryable_llm_error(exc):
                    raise
                if self.retry_base_delay > 0:
                    await asyncio.sleep(self.retry_base_delay * (2**attempt))

        raise RuntimeError("LLM request exhausted retries without a response")

    async def _generate_once(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": request.model or self.default_model,
            "messages": [
                message.model_dump() if hasattr(message, "model_dump") else message.dict()
                for message in request.messages
            ],
            "temperature": request.temperature,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        if request.response_format is not None:
            payload["response_format"] = request.response_format

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            result = await client.post(
                self._chat_completions_url(),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            result.raise_for_status()

        data = result.json()
        message = data["choices"][0]["message"]
        content = message.get("content", "") or ""
        if not content.strip():
            raise RuntimeError("LLM response content is empty")

        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=data.get("model"),
            usage=usage,
            raw=data,
        )

    def _chat_completions_url(self) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"


class DeepSeekLLMClient(OpenAICompatibleLLMClient):
    """DeepSeek Chat Completions client.

    DeepSeek 兼容 OpenAI Chat Completions 协议，所以复用 OpenAI-compatible 实现，
    但读取 `DEEPSEEK_*` 配置，避免要求用户再手动复制成 `OPENAI_*`。
    """

    def __init__(self, timeout: float = 60.0) -> None:
        load_env_file()
        super().__init__(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
            default_model=_deepseek_default_model(),
            timeout=timeout,
        )


"""
后续业务代码可以：
    llm_client = create_llm_client()
本地测试默认用 fake，不需要 API Key。
生产环境设置：
    LLM_CLIENT=openai
    OPENAI_API_KEY=...
"""
def create_llm_client(kind: str | None = None) -> LLMClient:
    load_env_file()
    client_kind = resolve_llm_client_kind(kind)

    if client_kind == "fake":
        return FakeLLMClient()

    if client_kind == "openai":
        return OpenAICompatibleLLMClient()

    if client_kind == "deepseek":
        return DeepSeekLLMClient()

    raise ValueError(f"Unsupported LLM client kind: {client_kind}")


def resolve_llm_client_kind(kind: str | None = None) -> str:
    """解析当前应使用的 LLM 客户端类型。

    优先使用显式 `LLM_CLIENT`；如果未配置但发现 DeepSeek Key，则自动启用 DeepSeek。
    """

    load_env_file()
    explicit_kind = kind or os.getenv("LLM_CLIENT")
    if explicit_kind:
        return explicit_kind.lower()

    if _looks_configured(os.getenv("DEEPSEEK_API_KEY")):
        return "deepseek"

    if _looks_configured(os.getenv("OPENAI_API_KEY")):
        return "openai"

    return "fake"


def _deepseek_default_model() -> str:
    return (
        os.getenv("DEEPSEEK_STRUCTURED_MODEL")
        or os.getenv("DEEPSEEK_MODEL")
        or os.getenv("DEEPSEEK_REASON_MODEL")
        or "deepseek-chat"
    )


def _looks_configured(value: str | None) -> bool:
    if value is None:
        return False
    stripped = value.strip()
    return bool(stripped and stripped.lower() not in {"your_api_key_here", "your_key", "changeme"})


def _is_retryable_llm_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code in {408, 409, 425, 429, 500, 502, 503, 504}
    return isinstance(exc, RuntimeError) and "response content is empty" in str(exc)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default
