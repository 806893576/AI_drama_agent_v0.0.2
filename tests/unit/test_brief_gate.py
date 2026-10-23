import pytest

from agents.brief_agent import analyze_brief
from domain.brief.validators import evaluate_brief_gate
from graph.edges import route_after_brief_gate
from graph.nodes.human_node import brief_gate_node
from schemas.enums import DecisionStatus, NodeId


def test_evaluate_brief_gate_passes_complete_brief() -> None:
    result = analyze_brief(
        "都市逆袭短剧，平台抖音，12集，每集2分钟，讲女主夺回公司。"
    )

    gate = evaluate_brief_gate(result.validation)

    assert gate.status == DecisionStatus.PASSED
    assert gate.next_node == NodeId.PRODUCER_ROUTER
    assert gate.is_complete is True


def test_evaluate_brief_gate_routes_missing_fields_to_human_confirm() -> None:
    result = analyze_brief("强爽点短剧。")

    gate = evaluate_brief_gate(result.validation)

    assert gate.status == DecisionStatus.NEEDS_USER_INPUT
    assert gate.next_node == NodeId.HUMAN_CONFIRM
    assert gate.is_complete is False
    assert gate.missing_fields
    assert gate.questions_for_user


def test_brief_gate_node_returns_partial_state_update() -> None:
    result = analyze_brief(
        "都市逆袭短剧，平台抖音，12集，每集2分钟，讲女主夺回公司。"
    )

    update = brief_gate_node(
        {
            "job_id": "job_001",
            "brief_validation": result.validation,
        }
    )

    assert update["brief_gate_result"].next_node == NodeId.PRODUCER_ROUTER
    assert update["next_node"] == NodeId.PRODUCER_ROUTER
    assert update["events"]


def test_brief_gate_node_requires_validation() -> None:
    with pytest.raises(ValueError):
        brief_gate_node({"job_id": "job_001"})


def test_route_after_brief_gate_prefers_gate_result() -> None:
    result = analyze_brief("强爽点短剧。")
    gate = evaluate_brief_gate(result.validation)

    assert route_after_brief_gate({"brief_gate_result": gate}) == NodeId.HUMAN_CONFIRM.value