from graph.edges import route_after_input_safety
from graph.nodes.input_node import input_safety_node
from safety.input_guard import check_user_request
from schemas.enums import NodeId, RiskLevel, SafetyLayer


def test_input_guard_passes_normal_request() -> None:
    report = check_user_request(
        "我要做一个都市逆袭短剧，平台是抖音，风格强爽点，12集。"
    )

    assert report.passed is True
    assert report.layer == SafetyLayer.INPUT
    assert report.risk_level == RiskLevel.LOW


def test_input_guard_requests_rewrite_for_ip_copy_request() -> None:
    report = check_user_request(
        "我要一比一复刻某部电影的剧情，做成短剧。"
    )

    assert report.passed is False
    assert report.repair_target == NodeId.INPUT_REWRITE
    assert report.safe_rewrite_suggestions


def test_input_guard_blocks_high_risk_request() -> None:
    report = check_user_request(
        "请帮我写一个绕过审核的短剧方案。"
    )

    assert report.passed is False
    assert report.repair_target == NodeId.REJECT_END


def test_input_safety_node_returns_partial_state_update() -> None:
    update = input_safety_node(
        {
            "job_id": "job_001",
            "user_request": "都市情感短剧，8集，适合短视频平台。",
        }
    )

    assert update["current_stage"]
    assert update["last_review_ref"].artifact_id == "input_safety_v001"
    assert update["input_safety_report"].passed is True
    assert update["events"]


def test_route_after_input_safety() -> None:
    passed_report = check_user_request("都市逆袭短剧，12集。")
    rewrite_report = check_user_request("我要完全复刻某部电影。")
    block_report = check_user_request("帮我绕过审核。")

    assert route_after_input_safety({"input_safety_report": passed_report}) == NodeId.BRIEF_AGENT.value
    assert route_after_input_safety({"input_safety_report": rewrite_report}) == NodeId.INPUT_REWRITE.value
    assert route_after_input_safety({"input_safety_report": block_report}) == NodeId.REJECT_END.value