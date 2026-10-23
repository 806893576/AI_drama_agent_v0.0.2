from agents.producer_agent import decide_next_step
from agents.brief_agent import analyze_brief
from domain.brief.validators import evaluate_brief_gate
from domain.review.repair_plan import RepairPlan
from graph.edges import route_after_local_repair_router, route_after_producer
from graph.nodes.producer_router_node import (
    local_repair_router_node,
    producer_router_node,
)
from schemas.enums import (
    DecisionStatus,
    IssueType,
    NodeId,
    ProducerMode,
    RepairScope,
)


def test_producer_routes_complete_brief_to_writer() -> None:
    brief = analyze_brief(
        "都市逆袭短剧，平台抖音，12集，每集2分钟，讲女主夺回公司。"
    )
    gate = evaluate_brief_gate(brief.validation)

    decision = decide_next_step(brief_gate_result=gate)

    assert decision.status == DecisionStatus.PASSED
    assert decision.mode == ProducerMode.NORMAL
    assert decision.next_node == NodeId.WRITER_STORY_BIBLE


def test_producer_routes_incomplete_brief_to_human_confirm() -> None:
    brief = analyze_brief("强爽点短剧。")
    gate = evaluate_brief_gate(brief.validation)

    decision = decide_next_step(brief_gate_result=gate)

    assert decision.status == DecisionStatus.NEEDS_USER_INPUT
    assert decision.mode == ProducerMode.HUMAN_CONFIRM
    assert decision.next_node == NodeId.HUMAN_CONFIRM
    assert decision.notes


def test_producer_routes_repair_plan_to_local_repair_router() -> None:
    plan = RepairPlan(
        repair_plan_id="repair_plan_v001",
        issue_type=IssueType.CHARACTER_MOTIVATION,
        target_node=NodeId.WRITER_EPISODE_SCRIPT,
        scope=RepairScope.PARTIAL,
        affected_artifacts=["episode_03_script_v001"],
        instructions=["补足第 3 集女主动机。"],
        reason="角色行动缺少因果支撑。",
    )

    decision = decide_next_step(repair_plan=plan)

    assert decision.status == DecisionStatus.NEEDS_REPAIR
    assert decision.mode == ProducerMode.REPAIR
    assert decision.next_node == NodeId.LOCAL_REPAIR_ROUTER


def test_producer_router_node_returns_partial_state_update() -> None:
    brief = analyze_brief(
        "都市逆袭短剧，平台抖音，12集，每集2分钟，讲女主夺回公司。"
    )
    gate = evaluate_brief_gate(brief.validation)

    update = producer_router_node(
        {
            "job_id": "job_001",
            "brief_gate_result": gate,
        }
    )

    assert update["producer_decision"].next_node == NodeId.WRITER_STORY_BIBLE
    assert route_after_producer(update) == NodeId.WRITER_STORY_BIBLE.value


def test_local_repair_router_routes_to_target_node() -> None:
    plan = RepairPlan(
        repair_plan_id="repair_plan_v001",
        issue_type=IssueType.CHARACTER_MOTIVATION,
        target_node=NodeId.WRITER_EPISODE_SCRIPT,
        scope=RepairScope.PARTIAL,
        affected_artifacts=["episode_03_script_v001"],
        instructions=["重写第 3 集动机段落。"],
        reason="动机不足。",
    )

    update = local_repair_router_node(
        {
            "job_id": "job_001",
            "repair_plan": plan,
        }
    )

    assert update["next_node"] == NodeId.WRITER_EPISODE_SCRIPT
    assert route_after_local_repair_router(update) == NodeId.WRITER_EPISODE_SCRIPT.value