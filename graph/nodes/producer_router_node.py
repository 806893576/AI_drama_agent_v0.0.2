"""制片人路由节点占位。

负责调用 Producer Agent 或规则路由器，根据当前阶段、审核报告、返工计划和重试次数选择下一步。
"""

from agents.producer_agent import decide_next_step
from domain.brief.validators import BriefGateResult
from domain.review.repair_plan import RepairPlan
from schemas.enums import EventStatus, NodeId, StageId
from state.events import RuntimeEvent

# 作用：把 Producer Router 包装成 LangGraph node 风格函数。
"""
LangGraph 节点只负责：
    读取 state
    调用 decide_next_step()
    返回局部 state update
它不直接写剧情，也不直接跳子图。
"""
def producer_router_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    brief_gate_result = _coerce_model(state.get("brief_gate_result"), BriefGateResult)
    repair_plan = _coerce_model(state.get("repair_plan"), RepairPlan)

    decision = decide_next_step(
        brief_gate_result=brief_gate_result,
        repair_plan=repair_plan,
        final_ready=state.get("final_ready", False),
    )

    event = RuntimeEvent(
        event_id=f"{job_id}_producer_router_completed",
        node_id=NodeId.PRODUCER_ROUTER,
        stage=StageId.PRODUCER,
        status=EventStatus.COMPLETED,
        message=decision.reason,
        artifact_ids=[],
    )

    return {
        "current_stage": StageId.PRODUCER,
        "producer_decision": decision,
        "next_node": decision.next_node,
        "events": [event],
    }


"""
具体作用：
这个节点不做复杂判断，只把：
    repair_plan.target_node
转成：
    next_node
也就是 V4 图里的：
    局部返工路由
    按 target_node 回流
"""
def local_repair_router_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    repair_plan = _coerce_model(state.get("repair_plan"), RepairPlan)

    if repair_plan is None:
        raise ValueError("repair_plan is required for local_repair_router_node")

    event = RuntimeEvent(
        event_id=f"{job_id}_local_repair_router_completed",
        node_id=NodeId.LOCAL_REPAIR_ROUTER,
        stage=StageId.REPAIR,
        status=EventStatus.COMPLETED,
        message=f"Route repair to {repair_plan.target_node.value}.",
        artifact_ids=[],
    )

    return {
        "current_stage": StageId.REPAIR,
        "next_node": repair_plan.target_node,
        "events": [event],
    }


def _coerce_model(value, model_type):
    if value is None or isinstance(value, model_type):
        return value
    if isinstance(value, dict):
        return model_type(**value)
    return value
