"""返工规划节点。"""

from __future__ import annotations

from domain.review.repair_plan import RepairPlan
from schemas.enums import ArtifactType, EventStatus, IssueType, NodeId, RepairScope, StageId
from services.llm import generate_model_with_fallback, json_dumps_for_prompt
from services.storage.artifact_store import ArtifactStore
from state.artifact_refs import get_artifact_ref_id
from state.events import RuntimeEvent


def repair_planner_node(state: dict) -> dict:
    """把失败报告转换为最小返工计划。

    真实 LLM 可根据失败类型选择更精确的 target_node；如果未启用模型或模型输出不可用，
    则回到规则兜底逻辑，保证图不会中断。
    """

    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    plan = generate_model_with_fallback(
        "agents.repair_planner",
        {"state_context": json_dumps_for_prompt(_repair_state_context(state))},
        RepairPlan,
        fallback=lambda: _build_rule_repair_plan(state),
        temperature=0.2,
    )

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.REPAIR_PLAN,
        content=plan,
        summary=plan.reason,
        created_by=NodeId.REPAIR_PLANNER,
    )
    event = RuntimeEvent(
        event_id=f"{job_id}_repair_planner_completed",
        node_id=NodeId.REPAIR_PLANNER,
        stage=StageId.REPAIR,
        status=EventStatus.COMPLETED,
        message=plan.reason,
        artifact_ids=[ref.artifact_id],
    )
    return {
        "current_stage": StageId.REPAIR,
        "artifact_refs": {"repair_plan": ref},
        "repair_plan": plan,
        "events": [event],
    }


def _build_rule_repair_plan(state: dict) -> RepairPlan:
    """规则兜底：根据最近失败报告选择最小返工节点。"""

    target_node = _choose_target_node(state)
    return RepairPlan(
        repair_plan_id="repair_plan_v001",
        issue_type=IssueType.SAFETY_RISK if "safety" in str(target_node.value) else IssueType.STORY_LOGIC,
        target_node=target_node,
        scope=RepairScope.NODE,
        affected_artifacts=[get_artifact_ref_id(state.get("last_review_ref"))] if state.get("last_review_ref") else [],
        keep_unchanged=["story_bible", "character_bible"],
        instructions=["保留已通过的一致性设定，只修复失败报告指出的局部问题。"],
        reason=f"根据审核结果回到 {target_node.value} 做局部返工。",
        max_retries=2,
    )


def _choose_target_node(state: dict) -> NodeId:
    for report_key in (
        "script_safety_report",
        "shot_av_safety_report",
        "prompt_safety_report",
        "final_safety_report",
    ):
        report = state.get(report_key)
        if report is not None and getattr(report, "repair_target", None) is not None:
            return report.repair_target

    quality = state.get("quality_score_report")
    if quality is not None and not getattr(quality, "passed", True):
        return NodeId.WRITER_EPISODE_SCRIPT

    production = state.get("production_continuity_report")
    if production is not None and not getattr(production, "passed", True):
        return NodeId.ASSET_MANAGER

    return NodeId.WRITER_DIALOGUE_POLISH


def _repair_state_context(state: dict) -> dict:
    """只发送返工规划所需的失败报告和产物引用。"""

    keys = [
        "last_review_ref",
        "script_review_report",
        "quality_score_report",
        "script_safety_report",
        "text_continuity_report",
        "shot_av_safety_report",
        "prompt_safety_report",
        "production_continuity_report",
        "final_safety_report",
        "artifact_refs",
    ]
    return {key: state.get(key) for key in keys if key in state}
