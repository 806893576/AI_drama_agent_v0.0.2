"""制片人 Agent / Supervisor Router 占位。

职责：读取轻量 DramaGraphState 和审核报告，决定下一节点、返工范围、人机确认点和最终验收。
该 Agent 应尽量输出结构化路由决策，避免承担具体创作任务。
"""

from domain.brief.validators import BriefGateResult
from domain.review.repair_plan import RepairPlan
from schemas.enums import DecisionStatus, NodeId, ProducerMode
from state.producer_decision import ProducerDecision


# 作用：封装制片人调度规则。
"""
这个类负责做顶层调度判断：
    有 repair_plan -> 去 local_repair_router
    brief 不完整 -> 去 human_confirm
    final_ready -> 去 final_output
    默认 -> 去 writer.story_bible
"""
class ProducerRouter:
    def decide_next_step(
        self,
        brief_gate_result: BriefGateResult | None = None,
        repair_plan: RepairPlan | None = None,
        final_ready: bool = False,
    ) -> ProducerDecision:
        if repair_plan is not None:
            return ProducerDecision(
                status=DecisionStatus.NEEDS_REPAIR,
                mode=ProducerMode.REPAIR,
                next_node=NodeId.LOCAL_REPAIR_ROUTER,
                reason=f"进入局部返工：{repair_plan.reason}",
                repair_plan_ref=repair_plan.repair_plan_id,
            )

        if brief_gate_result is not None and not brief_gate_result.is_complete:
            return ProducerDecision(
                status=DecisionStatus.NEEDS_USER_INPUT,
                mode=ProducerMode.HUMAN_CONFIRM,
                next_node=NodeId.HUMAN_CONFIRM,
                reason=brief_gate_result.reason,
                human_message="创作简报缺少关键信息，需要用户补充。",
                notes=brief_gate_result.questions_for_user,
            )

        if final_ready:
            return ProducerDecision(
                status=DecisionStatus.COMPLETED,
                mode=ProducerMode.END,
                next_node=NodeId.FINAL_OUTPUT,
                reason="所有阶段已完成，进入最终输出。",
            )

        return ProducerDecision(
            status=DecisionStatus.PASSED,
            mode=ProducerMode.NORMAL,
            next_node=NodeId.WRITER_STORY_BIBLE,
            reason="创作简报已满足启动条件，进入编剧子图。",
        )


# 提供便捷函数 decide_next_step()
"""
后续节点可以直接调用：
    decision = decide_next_step(...)
不需要自己实例化 ProducerRouter。
"""
def decide_next_step(
    brief_gate_result: BriefGateResult | None = None,
    repair_plan: RepairPlan | None = None,
    final_ready: bool = False,
) -> ProducerDecision:
    return ProducerRouter().decide_next_step(
        brief_gate_result=brief_gate_result,
        repair_plan=repair_plan,
        final_ready=final_ready,
    )