# 作用：保存制片人路由节点的结构化决策。


"""
Producer Router 后续不应该输出一段自然语言，而应该输出：
ProducerDecision(
    status=DecisionStatus.NEEDS_REPAIR,
    mode=ProducerMode.REPAIR,
    next_node=NodeId.LOCAL_REPAIR_ROUTER,
    reason="剧本质量评分未达标，进入局部返工。",
)
这样 LangGraph 条件边可以稳定判断。
"""
from pydantic import BaseModel, Field

from schemas.enums import DecisionStatus, NodeId, ProducerMode


"""
承载制片人路由/决策代理（Producer Router）的输出决策结果。
    status: 决策状态（类型为枚举 DecisionStatus，例如通过、需要返工、拒绝等，决定大局走向）。
    mode: 制片人工作模式（类型为枚举 ProducerMode，例如全自动运行、半自动、或者等待人工审批等模式）。
    next_node: 下一个执行的目标节点（类型为枚举 NodeId，可选。指明工作流接下来的流向，例如流转到导演节点、重试编剧节点或直接进入最终输出）。
    reason: 决策原因说明（详细解释为什么做出这个路由决定或状态判断）。
    repair_plan_ref: 返工计划引用（可选。如果状态是需要返工，这里会关联对应的修复计划 ID，供下游修复节点读取）。
    human_message: 提示给人类用户的消息（可选。如果当前处于需要人工审核或交互的模式，这里会向用户展示需要人工决策的提示信息）。
    notes: 备注或附加说明列表（默认空列表，用于记录制片决策过程中的其他补充信息或日志）。
"""
class ProducerDecision(BaseModel):
    status: DecisionStatus
    mode: ProducerMode
    next_node: NodeId | None = None
    reason: str
    repair_plan_ref: str | None = None
    human_message: str | None = None
    notes: list[str] = Field(default_factory=list)