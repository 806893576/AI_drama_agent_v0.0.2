"""功能：LLM 服务包，封装大模型调用和模型配置。"""

# 作用：统一导出 LLM 相关类和函数。
from services.llm.client import (
    DeepSeekLLMClient,
    FakeLLMClient,
    LLMClient,
    OpenAICompatibleLLMClient,
    create_llm_client,
    load_env_file,
    parse_json_response,
    parse_model_response,
    resolve_llm_client_kind,
)
from services.llm.context import (
    render_character_bible_context,
    render_creative_brief_context,
    render_creative_context,
    render_episode_outline_context,
    render_episode_scripts_context,
    render_story_bible_context,
    render_story_synopsis_context,
)
from services.llm.models import LLMMessage, LLMRequest, LLMResponse
from services.llm.structured import (
    LLMRuntimeError,
    LLMStructuredOutputError,
    StructuredLLMRunner,
    generate_model_with_fallback,
    json_dumps_for_prompt,
    llm_enabled,
    structured_output_mode,
)
from services.llm.trace import LLMTraceStore, llm_trace_context

__all__ = [
    "FakeLLMClient",
    "DeepSeekLLMClient",
    "LLMClient",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "OpenAICompatibleLLMClient",
    "LLMRuntimeError",
    "LLMStructuredOutputError",
    "LLMTraceStore",
    "StructuredLLMRunner",
    "create_llm_client",
    "generate_model_with_fallback",
    "json_dumps_for_prompt",
    "llm_enabled",
    "llm_trace_context",
    "load_env_file",
    "parse_json_response",
    "parse_model_response",
    "resolve_llm_client_kind",
    "render_character_bible_context",
    "render_creative_brief_context",
    "render_creative_context",
    "render_episode_outline_context",
    "render_episode_scripts_context",
    "render_story_bible_context",
    "render_story_synopsis_context",
    "structured_output_mode",
]
