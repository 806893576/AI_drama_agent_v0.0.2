import json

import pytest

from agents.brief_agent import BriefAgent
from domain.brief.schemas import CreativeBrief
from services.llm import (
    FakeLLMClient,
    LLMRuntimeError,
    LLMStructuredOutputError,
    LLMTraceStore,
    StructuredLLMRunner,
    llm_trace_context,
    structured_output_mode,
)
from services.llm.models import LLMRequest, LLMResponse


def test_brief_agent_uses_llm_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("LLM_CLIENT", "openai")
    fake = FakeLLMClient(
        response_content=(
            '{"genre":"都市逆袭","sub_genre":null,"platform":"抖音","audience":null,'
            '"episode_count":12,"episode_duration_minutes":2,"tone":"强爽点、快节奏",'
            '"style_keywords":["强爽点","快节奏"],"story_seed":"女主夺回主动权",'
            '"constraints":[],"forbidden_elements":[]}'
        )
    )
    agent = BriefAgent(llm_runner=StructuredLLMRunner(client=fake))

    result = agent.analyze("都市逆袭短剧，平台抖音，12集，每集2分钟。")

    assert result.used_llm is True
    assert result.creative_brief.genre == "都市逆袭"
    assert result.creative_brief.platform == "抖音"
    assert result.validation.is_complete is True


def test_brief_agent_interrupts_when_llm_returns_invalid_json(monkeypatch) -> None:
    monkeypatch.setenv("LLM_CLIENT", "openai")
    fake = FakeLLMClient(response_content="not-json")
    agent = BriefAgent(llm_runner=StructuredLLMRunner(client=fake))

    with pytest.raises(LLMStructuredOutputError) as exc_info:
        agent.analyze("都市逆袭短剧，平台抖音，12集，每集2分钟。")

    assert exc_info.value.prompt_id == "brief_agent"
    assert "not-json" in exc_info.value.raw_output


def test_structured_runner_extracts_markdown_json(monkeypatch) -> None:
    monkeypatch.setenv("LLM_CLIENT", "openai")
    fake = FakeLLMClient(
        response_content=(
            "```json\n"
            '{"genre":"都市逆袭","platform":"抖音","episode_count":12,'
            '"episode_duration_minutes":2,"tone":null,"style_keywords":[],'
            '"story_seed":"女主夺回主动权","constraints":[],"forbidden_elements":[]}'
            "\n```"
        )
    )

    brief, _response = StructuredLLMRunner(client=fake).generate_model(
        "brief_agent",
        {"user_request": "都市逆袭短剧，平台抖音，12集，每集2分钟。"},
        CreativeBrief,
    )

    assert brief.genre == "都市逆袭"
    assert brief.platform == "抖音"


def test_structured_runner_writes_success_trace(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_CLIENT", "openai")
    fake = FakeLLMClient(
        response_content=(
            '{"genre":"都市逆袭","platform":"抖音","episode_count":12,'
            '"episode_duration_minutes":2,"tone":null,"style_keywords":[],'
            '"story_seed":"女主夺回主动权","constraints":[],"forbidden_elements":[]}'
        )
    )
    runner = StructuredLLMRunner(client=fake, trace_store=LLMTraceStore(root_dir=tmp_path))

    with llm_trace_context("job_trace_unit"):
        brief, _response = runner.generate_model(
            "brief_agent",
            {"user_request": "都市逆袭短剧，平台抖音，12集，每集2分钟。"},
            CreativeBrief,
        )

    trace_files = list((tmp_path / "job_trace_unit").glob("*.json"))
    assert len(trace_files) == 1

    payload = json.loads(trace_files[0].read_text(encoding="utf-8"))
    assert payload["prompt_id"] == "brief_agent"
    assert payload["trace_id"]
    assert payload["status"] == "success"
    assert payload["usage"] == {"prompt_tokens": 0, "completion_tokens": 0}
    assert payload["parsed_result"]["genre"] == brief.genre
    assert "raw_output" in payload
    assert payload["prompt_trace_path"]

    prompt_files = list((tmp_path / "job_trace_unit" / "prompts").glob("*.json"))
    assert len(prompt_files) == 1
    prompt_payload = json.loads(prompt_files[0].read_text(encoding="utf-8"))
    assert prompt_payload["trace_id"] == payload["trace_id"]
    assert prompt_payload["prompt_id"] == "brief_agent"
    assert prompt_payload["messages"][0]["role"] == "system"
    assert prompt_payload["messages"][1]["role"] == "user"
    assert "都市逆袭短剧" in prompt_payload["messages"][1]["content"]


def test_structured_runner_writes_error_trace(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_CLIENT", "openai")
    fake = FakeLLMClient(response_content="not-json")
    runner = StructuredLLMRunner(client=fake, trace_store=LLMTraceStore(root_dir=tmp_path))

    with llm_trace_context("job_trace_error"), pytest.raises(LLMStructuredOutputError):
        runner.generate_model(
            "brief_agent",
            {"user_request": "都市逆袭短剧，平台抖音，12集，每集2分钟。"},
            CreativeBrief,
        )

    trace_files = list((tmp_path / "job_trace_error").glob("*.json"))
    assert len(trace_files) == 1

    payload = json.loads(trace_files[0].read_text(encoding="utf-8"))
    assert payload["prompt_id"] == "brief_agent"
    assert payload["status"] == "structured_output_error"
    assert payload["prompt_trace_path"]
    assert payload["raw_output"] == "not-json"
    assert payload["error_type"] == "ValueError"
    assert payload["target_schema"]["title"] == "CreativeBrief"


class SequentialLLMClient(FakeLLMClient):
    def __init__(self, responses: list[str]) -> None:
        super().__init__(response_content="")
        self.responses = responses

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            content=self.responses.pop(0),
            model=request.model or "fake-model",
            usage={"prompt_tokens": 0, "completion_tokens": 0},
            raw={},
        )


class FailingLLMClient(FakeLLMClient):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        raise OSError(
            "[SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC] decryption failed or bad record mac"
        )


def test_structured_runner_auto_repairs_after_confirmation(monkeypatch) -> None:
    monkeypatch.setenv("LLM_CLIENT", "openai")
    client = SequentialLLMClient(
        [
            "not-json",
            (
                '{"genre":"都市逆袭","platform":"抖音","episode_count":12,'
                '"episode_duration_minutes":2,"tone":null,"style_keywords":[],'
                '"story_seed":"女主夺回主动权","constraints":[],"forbidden_elements":[]}'
            ),
        ]
    )

    with structured_output_mode("auto_repair"):
        brief, _response = StructuredLLMRunner(client=client).generate_model(
            "brief_agent",
            {"user_request": "都市逆袭短剧，平台抖音，12集，每集2分钟。"},
            CreativeBrief,
        )

    assert brief.genre == "都市逆袭"
    assert len(client.requests) == 2
    assert client.requests[1].metadata["prompt_id"] == "brief_agent.format_repair"


def test_structured_runner_exposes_runtime_error(monkeypatch) -> None:
    monkeypatch.setenv("LLM_CLIENT", "openai")
    client = FailingLLMClient(response_content="")

    with pytest.raises(LLMRuntimeError) as exc_info:
        StructuredLLMRunner(client=client).generate_model(
            "brief_agent",
            {"user_request": "都市逆袭短剧，平台抖音，12集，每集2分钟。"},
            CreativeBrief,
        )

    assert exc_info.value.prompt_id == "brief_agent"
    assert "DECRYPTION_FAILED_OR_BAD_RECORD_MAC" in exc_info.value.error_message
