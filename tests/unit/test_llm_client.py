import httpx
import pytest
from pydantic import BaseModel

from services.llm import (
    DeepSeekLLMClient,
    FakeLLMClient,
    LLMMessage,
    LLMRequest,
    OpenAICompatibleLLMClient,
    create_llm_client,
    parse_json_response,
    parse_model_response,
    resolve_llm_client_kind,
)


class DemoModel(BaseModel):
    title: str


@pytest.mark.asyncio
async def test_fake_llm_client_returns_deterministic_response() -> None:
    client = FakeLLMClient(response_content='{"title": "测试短剧"}')

    response = await client.generate(
        LLMRequest(
            messages=[
                LLMMessage(role="system", content="你是短剧编剧。"),
                LLMMessage(role="user", content="生成标题。"),
            ]
        )
    )

    assert response.content == '{"title": "测试短剧"}'
    assert len(client.requests) == 1


def test_parse_json_response() -> None:
    client = FakeLLMClient(response_content='{"title": "测试短剧"}')
    response = client.response_content

    parsed = parse_json_response(type("Resp", (), {"content": response})())

    assert parsed["title"] == "测试短剧"


@pytest.mark.asyncio
async def test_parse_model_response() -> None:
    client = FakeLLMClient(response_content='{"title": "测试短剧"}')
    response = await client.generate(LLMRequest(messages=[]))

    model = parse_model_response(response, DemoModel)

    assert model.title == "测试短剧"


def test_create_fake_llm_client_when_explicitly_configured(monkeypatch) -> None:
    monkeypatch.setenv("LLM_CLIENT", "fake")

    client = create_llm_client()

    assert isinstance(client, FakeLLMClient)


def test_create_deepseek_client_from_deepseek_env(monkeypatch) -> None:
    monkeypatch.setenv("LLM_CLIENT", "")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_STRUCTURED_MODEL", "deepseek-chat")

    client = create_llm_client()

    assert resolve_llm_client_kind() == "deepseek"
    assert isinstance(client, DeepSeekLLMClient)
    assert client.base_url == "https://api.deepseek.com"
    assert client.default_model == "deepseek-chat"


@pytest.mark.asyncio
async def test_openai_compatible_client_retries_transport_errors() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.RemoteProtocolError("peer closed connection")
        return httpx.Response(
            200,
            json={
                "model": "demo-model",
                "choices": [{"message": {"content": '{"title":"ok"}'}}],
                "usage": {"total_tokens": 3},
            },
        )

    client = OpenAICompatibleLLMClient(
        api_key="test-key",
        base_url="https://example.test",
        default_model="demo-model",
        max_retries=1,
        retry_base_delay=0,
        transport=httpx.MockTransport(handler),
    )

    response = await client.generate(LLMRequest(messages=[]))

    assert calls == 2
    assert response.content == '{"title":"ok"}'


@pytest.mark.asyncio
async def test_openai_compatible_client_retries_empty_content() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        content = "" if calls == 1 else '{"title":"ok"}'
        return httpx.Response(
            200,
            json={
                "model": "demo-model",
                "choices": [{"message": {"content": content}}],
                "usage": {"total_tokens": calls},
            },
        )

    client = OpenAICompatibleLLMClient(
        api_key="test-key",
        base_url="https://example.test",
        default_model="demo-model",
        max_retries=1,
        retry_base_delay=0,
        transport=httpx.MockTransport(handler),
    )

    response = await client.generate(LLMRequest(messages=[]))

    assert calls == 2
    assert response.content == '{"title":"ok"}'


@pytest.mark.asyncio
async def test_generate_sync_works_inside_running_event_loop() -> None:
    client = FakeLLMClient(response_content='{"title": "loop-safe"}')

    response = client.generate_sync(LLMRequest(messages=[]))

    assert response.content == '{"title": "loop-safe"}'
