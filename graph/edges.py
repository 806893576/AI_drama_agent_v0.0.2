"""主图条件边定义占位。

用于根据 ProducerDecision、ReviewReport、RepairPlan、QualityScore、SafetyRisk
和 retry_count 选择下一节点。条件边应尽量读取结构化字段，减少自然语言判断。
"""

from graph.execution_options import get_execution_options
from schemas.enums import NodeId


def _confirmed_human_points(state: dict) -> set[str]:
    return {str(point) for point in state.get("confirmed_human_points", [])}


def _should_pause_for_confirmation(state: dict, point: str) -> bool:
    options = get_execution_options(state)
    return options.enable_human_confirmations and point not in _confirmed_human_points(state)


def _field(value, key: str, default=None):
    """兼容 Pydantic 对象和 checkpoint JSON dict 的字段读取。"""

    if value is None:
        return default
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _node_value(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return value.value
    return str(value)


def _next_after_writer(state: dict) -> str:
    options = get_execution_options(state)
    if options.run_script_review:
        return NodeId.SCRIPT_REVIEWER.value
    if options.run_quality_scoring:
        return NodeId.QUALITY_SCORING.value
    return _next_after_quality(state)


def _next_after_script_review(state: dict) -> str:
    options = get_execution_options(state)
    if options.run_quality_scoring:
        return NodeId.QUALITY_SCORING.value
    return _next_after_quality(state)


def _next_after_quality(state: dict) -> str:
    options = get_execution_options(state)
    if options.run_script_safety:
        return NodeId.SCRIPT_SAFETY.value
    return _next_after_script_safety(state)


def _next_after_script_safety(state: dict) -> str:
    options = get_execution_options(state)
    if options.run_text_continuity:
        return NodeId.TEXT_CONTINUITY.value
    return NodeId.DIRECTOR_SCENE_BREAKDOWN.value


def _next_after_audiovisual(state: dict) -> str:
    options = get_execution_options(state)
    if options.run_shot_av_safety:
        return NodeId.SHOT_AV_SAFETY.value
    return NodeId.ART_AGENT.value


def _next_after_art(state: dict) -> str:
    options = get_execution_options(state)
    if options.run_prompt_safety:
        return NodeId.PROMPT_SAFETY.value
    return NodeId.ASSET_MANAGER.value


def _next_after_asset(state: dict) -> str:
    options = get_execution_options(state)
    if options.run_production_continuity:
        return NodeId.PRODUCTION_CONTINUITY.value
    return _next_after_production_continuity(state)


def _next_after_production_continuity(state: dict) -> str:
    options = get_execution_options(state)
    if options.run_final_safety:
        return NodeId.FINAL_SAFETY.value
    return _next_after_final_safety(state)


def _next_after_final_safety(state: dict) -> str:
    options = get_execution_options(state)
    if options.run_final_acceptance:
        return NodeId.FINAL_ACCEPTANCE.value
    return NodeId.FINAL_OUTPUT.value


# 作用：根据 SafetyReviewReport 决定下一步走向。
"""
把 V4 图中的条件边落成代码：
    输入安全通过 -> brief_agent
    输入需要改写 -> input_rewrite
    输入不可继续 -> reject_end
后续 LangGraph 主图中会使用：
builder.add_conditional_edges(
    "input_safety",
    route_after_input_safety,
    {
        "brief_agent": "brief_agent",
        "input_rewrite": "input_rewrite",
        "reject_end": END,
    },
)
"""
def route_after_input_safety(state: dict) -> str:
    """
    在第一次进入route_after_input_safety之前，已经更新了
    return {
        "current_stage": StageId.SAFETY,
        "last_review_ref": review_ref,
        "input_safety_report": report,
        "events": [event],
    }
    """
    report = state.get("input_safety_report")

    if report is None:
        return NodeId.INPUT_REWRITE.value

    if _field(report, "passed", False):
        return NodeId.BRIEF_AGENT.value

    if _node_value(_field(report, "repair_target")) == NodeId.REJECT_END.value:
        return NodeId.REJECT_END.value

    return NodeId.INPUT_REWRITE.value


# 作用：根据 BriefValidation 判断下一步。
"""
兼容两种情况：
    已经跑过 brief_gate_node -> 读取 brief_gate_result
    还没跑 brief_gate_node -> 临时根据 brief_validation 判断
后续正式主图中推荐：
    brief_agent_node -> brief_gate_node -> conditional edge
"""
def route_after_brief_gate(state: dict) -> str:
    gate_result = state.get("brief_gate_result")

    if gate_result is not None:
        next_node = _node_value(_field(gate_result, "next_node")) or NodeId.HUMAN_CONFIRM.value
        if next_node == NodeId.PRODUCER_ROUTER.value and _should_pause_for_confirmation(state, "brief"):
            return NodeId.HUMAN_BRIEF_CONFIRM.value
        return next_node

    validation = state.get("brief_validation")

    if validation is None:
        return NodeId.HUMAN_CONFIRM.value

    if _field(validation, "is_complete", False):
        if _should_pause_for_confirmation(state, "brief"):
            return NodeId.HUMAN_BRIEF_CONFIRM.value
        return NodeId.PRODUCER_ROUTER.value

    return NodeId.HUMAN_CONFIRM.value


def route_after_style_guide(state: dict) -> str:
    if _should_pause_for_confirmation(state, "style"):
        return NodeId.HUMAN_STYLE_CONFIRM.value
    return NodeId.PRODUCER_ROUTER.value



# 作用：LangGraph 条件边读取 ProducerDecision 后决定下一节点。
"""
后续主图中：
builder.add_conditional_edges(
    "producer_router",
    route_after_producer,
    {
        "writer.story_bible": "writer_subgraph",
        "local_repair_router": "local_repair_router",
        "human_confirm": "human_confirm",
        "final_output": "final_output",
    },
)
"""
"""
return {
    "current_stage": StageId.PRODUCER,
    "producer_decision": decision,
    "next_node": decision.next_node,
    "events": [event],
}
decision = ProducerDecision(
    status=DecisionStatus.PASSED,
    mode=ProducerMode.NORMAL,
    next_node=NodeId.WRITER_STORY_BIBLE,
    reason="创作简报已满足启动条件，进入编剧子图。",
)
"""
def route_after_producer(state: dict) -> str:
    decision = state.get("producer_decision")

    next_node = _field(decision, "next_node")
    if decision is None or next_node is None:
        return NodeId.HUMAN_CONFIRM.value

    return _node_value(next_node) or NodeId.HUMAN_CONFIRM.value


# 具体作用：这个函数把 RepairPlan.target_node 映射到具体子图入口。
"""
后续主图中可以配置：
builder.add_conditional_edges(
    "local_repair_router",
    route_after_local_repair_router,
    {
        "writer.story_bible": "writer_subgraph",
        "writer.episode_script": "writer_subgraph",
        "director.shot_design": "director_subgraph",
        "av.enhancement": "audiovisual_subgraph",
        "art_agent": "art_agent",
        "asset_manager": "asset_manager",
    },
)
"""
def route_after_local_repair_router(state: dict) -> str:
    next_node = state.get("next_node")

    if next_node is None:
        return NodeId.HUMAN_CONFIRM.value

    return _node_value(next_node) or NodeId.HUMAN_CONFIRM.value


def route_after_writer_subgraph(state: dict) -> str:
    if state.get("human_confirmation_required"):
        return NodeId.HUMAN_CONFIRM.value
    return _next_after_writer(state)


def route_after_script_reviewer(state: dict) -> str:
    return _next_after_script_review(state)


def route_after_quality_scoring(state: dict) -> str:
    report = state.get("quality_score_report")
    if report is not None and _field(report, "passed", False):
        return _next_after_quality(state)
    return NodeId.REPAIR_PLANNER.value


def route_after_safety(state: dict, report_key: str, passed_node: NodeId) -> str:
    """安全分级节点通用路由。

    通过则进入下一阶段；不通过则统一进入 Repair Planner，由它决定局部返工目标。
    """

    report = state.get(report_key)
    if report is not None and _field(report, "passed", False):
        return passed_node.value
    return NodeId.REPAIR_PLANNER.value


def route_after_script_safety(state: dict) -> str:
    report = state.get("script_safety_report")
    if report is not None and _field(report, "passed", False):
        return _next_after_script_safety(state)
    return NodeId.REPAIR_PLANNER.value


def route_after_shot_av_safety(state: dict) -> str:
    return route_after_safety(state, "shot_av_safety_report", NodeId.ART_AGENT)


def route_after_prompt_safety(state: dict) -> str:
    return route_after_safety(state, "prompt_safety_report", NodeId.ASSET_MANAGER)


def route_after_final_safety(state: dict) -> str:
    report = state.get("final_safety_report")
    if report is not None and _field(report, "passed", False):
        return _next_after_final_safety(state)
    return NodeId.REPAIR_PLANNER.value


def route_after_continuity(state: dict, report_key: str, passed_node: NodeId) -> str:
    report = state.get(report_key)
    if report is not None and _field(report, "passed", False):
        return passed_node.value
    return NodeId.REPAIR_PLANNER.value


def route_after_text_continuity(state: dict) -> str:
    return route_after_continuity(state, "text_continuity_report", NodeId.DIRECTOR_SCENE_BREAKDOWN)


def route_after_production_continuity(state: dict) -> str:
    report = state.get("production_continuity_report")
    if report is not None and _field(report, "passed", False):
        return _next_after_production_continuity(state)
    return NodeId.REPAIR_PLANNER.value


def route_after_final_acceptance(state: dict) -> str:
    report = state.get("final_acceptance_report", {})
    if report.get("passed"):
        return NodeId.FINAL_OUTPUT.value
    return NodeId.REPAIR_PLANNER.value


def route_after_audiovisual_subgraph(state: dict) -> str:
    return _next_after_audiovisual(state)


def route_after_art_agent(state: dict) -> str:
    return _next_after_art(state)


def route_after_asset_manager(state: dict) -> str:
    return _next_after_asset(state)
