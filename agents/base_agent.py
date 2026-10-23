"""Agent 基础类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar


T = TypeVar("T")


@dataclass(slots=True)
class AgentContext:
    """Agent 运行上下文。

    Graph State 仍是全局状态源，这里只抽取 Agent 需要的轻量信息，
    避免业务 Agent 直接依赖 LangGraph 的状态结构。
    """

    job_id: str
    user_request: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentResult(Generic[T]):
    """统一 Agent 返回对象，方便后续追加 token、耗时、模型名等元数据。"""

    output: T
    summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(Generic[T]):
    """所有 Agent 的最小接口。"""

    name: str = "base_agent"

    def run(self, context: AgentContext, **kwargs: Any) -> AgentResult[T]:
        raise NotImplementedError
