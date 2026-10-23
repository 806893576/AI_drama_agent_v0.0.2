"""Graph 执行选项。

这些开关用于控制主图是否执行某些高成本节点。默认全开，保证和原来的
完整 v4 流程兼容；调用方可以按任务关闭部分审核节点以节省 token。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecutionOptions(BaseModel):
    """一次任务的节点执行策略。"""

    run_input_safety: bool = True
    run_script_review: bool = True
    run_quality_scoring: bool = True
    run_script_safety: bool = True
    run_text_continuity: bool = True
    run_shot_av_safety: bool = True
    run_prompt_safety: bool = True
    run_production_continuity: bool = True
    run_final_safety: bool = True
    run_final_acceptance: bool = True
    enable_human_confirmations: bool = False
    skipped_reason: str | None = Field(default=None, description="记录本次跳过部分节点的原因")

    @classmethod
    def fast_draft(cls) -> "ExecutionOptions":
        """快速草案模式：跳过大部分审核节点，保留最终输出。"""

        return cls(
            run_script_review=False,
            run_quality_scoring=False,
            run_script_safety=False,
            run_text_continuity=False,
            run_shot_av_safety=False,
            run_prompt_safety=False,
            run_production_continuity=False,
            run_final_safety=False,
            run_final_acceptance=False,
            skipped_reason="fast_draft",
        )


def get_execution_options(state: dict[str, Any]) -> ExecutionOptions:
    """从 state 中读取执行选项。

    支持传入 ExecutionOptions、dict 或 None。None 时使用完整执行策略。
    """

    raw = state.get("execution_options")
    if isinstance(raw, ExecutionOptions):
        return raw
    if isinstance(raw, dict):
        return ExecutionOptions(**raw)
    return ExecutionOptions()
