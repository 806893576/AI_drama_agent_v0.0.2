"""Repair Planner / 返工计划模型占位。

用于描述问题来源、影响产物、最小返工范围、目标节点、保留不变项、返工指令和最大重试次数。
"""

# 作用：这是整个局部返工机制的核心。所有失败报告都应该被 Repair Planner 转成 RepairPlan。
from pydantic import BaseModel, Field, field_validator

from schemas.enums import IssueType, NodeId, RepairScope


"""
具体作用：
例如剧本审核失败后，Repair Planner 可以输出：
RepairPlan(
    repair_plan_id="repair_plan_v001",
    issue_type=IssueType.CHARACTER_MOTIVATION,
    target_node=NodeId.WRITER_EPISODE_SCRIPT,
    scope=RepairScope.PARTIAL,
    affected_artifacts=["episode_03_script_v001"],
    keep_unchanged=["story_bible_v001", "character_bible_v001"],
    instructions=["补足女主在第 3 集选择反击的动机。"],
    reason="第 3 集女主行动转折缺少外部压力。",
)
Producer Router 后续只需要读：
repair_plan.target_node
就知道该回到哪个节点。
"""
"""
承载“返工规划节点（Repair Planner）”的修复计划与策略
    repair_plan_id: 修复计划的唯一标识符。
    issue_type: 触发返工的问题类型（类型为枚举 IssueType，例如剧情逻辑漏洞、安全违规等）。
    target_node: 建议回滚或重新执行的目标节点（类型为枚举 NodeId，指明应该回到哪一个历史工作流节点重新生成内容，如编剧节点或对白润色节点）。
    scope: 修复的作用范围（类型为枚举 RepairScope，例如局部修改 PARTIAL 还是全局重写）。
    affected_artifacts: 受影响的产物列表（默认空列表，记录需要被修复或更新的具体文件/数据对象）。
    keep_unchanged: 保持不变的内容列表（默认空列表，指导 AI 在返工时必须锁定、不得随意篡改的既定设定或资产，防止“改坏”）。
    instructions: 具体修复指令列表（默认空列表，为后续的 Agent 提供明确的修改步骤和整改要求）。
    reason: 返工的原因说明（解释为什么要进行这次修复）。
    max_retries: 最大重试次数（默认值为 2，限制该返工计划最多允许尝试修复几次，防止死循环）。
"""
class RepairPlan(BaseModel):
    repair_plan_id: str
    issue_type: IssueType
    target_node: NodeId
    scope: RepairScope
    affected_artifacts: list[str] = Field(default_factory=list)
    keep_unchanged: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    reason: str
    max_retries: int = 2

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_retries must be at least 1")
        if value > 5:
            raise ValueError("max_retries should not be greater than 5")
        return value