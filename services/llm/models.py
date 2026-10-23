"""功能：模型配置，维护短剧规划、写作、审核等场景使用的模型参数。"""

# 作用：统一模型调用输入输出结构。
from typing import Any, Literal

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


"""
后续每个 Agent 都可以构造：
LLMRequest(
    messages=[
        LLMMessage(role="system", content="你是短剧编剧。"),
        LLMMessage(role="user", content="请生成故事梗概。"),
    ],
    model="gpt-4.1-mini",
)
然后拿到统一的：
    LLMResponse(content="...")
"""
class LLMRequest(BaseModel):
    messages: list[LLMMessage]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    response_format: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    content: str
    model: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)