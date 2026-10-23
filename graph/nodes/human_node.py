"""功能：人工介入节点，在需要用户确认题材、风格、角色设定或修改意见时暂停工作流。"""

from domain.brief.validators import evaluate_brief_gate
from domain.human_confirmation import (
    BRIEF_CONFIRMATION_POINT,
    EPISODE_OUTLINE_CONFIRMATION_POINT,
    STYLE_CONFIRMATION_POINT,
)
from schemas.enums import EventStatus, NodeId, StageId
from state.events import RuntimeEvent

# 但为了保持节点文件数量少，本步骤建议先放在 human_node.py。因为 Brief Gate 失败后会进入人机确认，它和 Human Confirm 逻辑比较接近。
"""
这个节点把第 11 步的 brief_validation 转成正式路由决策。
    输入：
    {
        "brief_validation": BriefValidation(...)
        return BriefValidation(
            is_complete=not missing_fields,
            missing_fields=missing_fields,
            assumptions=[],
            questions_for_user=questions)
    )
    }
    输出：
    {
        "brief_gate_result": BriefGateResult(...),
        "next_node": NodeId.PRODUCER_ROUTER 或 NodeId.HUMAN_CONFIRM,
    }
"""
def brief_gate_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    validation = state.get("brief_validation")

    if validation is None:
        raise ValueError("brief_validation is required before brief_gate_node")

    gate_result = evaluate_brief_gate(validation)

    event = RuntimeEvent(
        event_id=f"{job_id}_brief_gate_completed",
        node_id=NodeId.BRIEF_GATE,
        stage=StageId.BRIEF,
        status=EventStatus.COMPLETED,
        message=gate_result.reason,
        artifact_ids=[],
    )

    return {
        "current_stage": StageId.BRIEF,
        "brief_gate_result": gate_result,
        "next_node": gate_result.next_node,
        "events": [event],
    }


# 作用：主图遇到“需要用户补充”或“输入被拒绝”时，有明确终点或暂停点。
# human_confirm_node()：表示流程暂停，等待用户补充信息；
def human_confirm_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    gate_result = state.get("brief_gate_result")

    questions = list(state.get("human_questions") or [])
    if gate_result is not None:
        questions = questions or gate_result.questions_for_user

    event = RuntimeEvent(
        event_id=f"{job_id}_human_confirm_required",
        node_id=NodeId.HUMAN_CONFIRM,
        stage=StageId.BRIEF,
        status=EventStatus.WAITING_FOR_USER,
        message="Waiting for user confirmation or missing brief fields.",
        artifact_ids=[],
    )

    return {
        "current_stage": StageId.BRIEF,
        "human_confirmation_required": True,
        "human_confirmation_point": state.get("human_confirmation_point"),
        "editable_artifact_refs": state.get("editable_artifact_refs", {}),
        "resume_target_node": state.get("resume_target_node"),
        "human_questions": questions,
        "events": [event],
    }


def human_brief_confirm_node(state: dict) -> dict:
    return _human_confirmation_pause(
        state,
        point=BRIEF_CONFIRMATION_POINT,
        title="创意简报确认",
        node_id=NodeId.HUMAN_BRIEF_CONFIRM,
        stage=StageId.BRIEF,
        editable_artifact_keys=["creative_brief"],
        resume_target_node=NodeId.STYLE_GUIDE.value,
        questions=[
            "请确认题材、平台、集数、单集时长、故事种子和整体剧情方向是否正确。",
            "如需修改，可用自然语言描述调整意见，或直接编辑 creative_brief JSON。",
        ],
    )


def human_style_confirm_node(state: dict) -> dict:
    return _human_confirmation_pause(
        state,
        point=STYLE_CONFIRMATION_POINT,
        title="创作风格确认",
        node_id=NodeId.HUMAN_STYLE_CONFIRM,
        stage=StageId.BRIEF,
        editable_artifact_keys=["style_guide"],
        resume_target_node=NodeId.PRODUCER_ROUTER.value,
        questions=[
            "请确认美术风格、导演风格、色彩、光影、镜头语言和禁止事项是否符合预期。",
            "如需修改，可用自然语言描述风格调整意见，或直接编辑 style_guide JSON。",
        ],
    )


def human_episode_outline_confirm_node(state: dict) -> dict:
    return _human_confirmation_pause(
        state,
        point=EPISODE_OUTLINE_CONFIRMATION_POINT,
        title="分集大纲确认",
        node_id=NodeId.HUMAN_EPISODE_OUTLINE_CONFIRM,
        stage=StageId.WRITER,
        editable_artifact_keys=["episode_outline"],
        resume_target_node=NodeId.WRITER_EPISODE_SCRIPT.value,
        questions=[
            "请确认每一集的定位、开场钩子、核心冲突、关键事件和结尾钩子是否符合预期。",
            "如需修改，可用自然语言描述某几集的调整意见，或直接编辑 episode_outline JSON。",
        ],
    )


def _human_confirmation_pause(
    state: dict,
    *,
    point: str,
    title: str,
    node_id: NodeId,
    stage: StageId,
    editable_artifact_keys: list[str],
    resume_target_node: str,
    questions: list[str],
) -> dict:
    job_id = state.get("job_id", "job_unknown")
    artifact_refs = state.get("artifact_refs", {})
    editable_refs = {
        key: artifact_refs[key]
        for key in editable_artifact_keys
        if key in artifact_refs
    }
    event = RuntimeEvent(
        event_id=f"{job_id}_{node_id.value}_required",
        node_id=node_id,
        stage=stage,
        status=EventStatus.WAITING_FOR_USER,
        message=f"{title}等待用户确认或修改。",
        artifact_ids=[
            ref.artifact_id if hasattr(ref, "artifact_id") else ref.get("artifact_id")
            for ref in editable_refs.values()
        ],
    )
    return {
        "current_stage": stage,
        "human_confirmation_required": True,
        "human_confirmation_point": point,
        "editable_artifact_refs": editable_refs,
        "resume_target_node": resume_target_node,
        "human_questions": questions,
        "final_message": f"{title}等待确认。",
        "events": [event],
    }


# reject_end_node()：表示安全拒绝，流程结束。
def reject_end_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")

    event = RuntimeEvent(
        event_id=f"{job_id}_request_rejected",
        node_id=NodeId.REJECT_END,
        stage=StageId.INPUT,
        status=EventStatus.COMPLETED,
        message="User request rejected by input safety guard.",
        artifact_ids=[],
    )

    return {
        "current_stage": StageId.INPUT,
        "terminated": True,
        "final_message": "输入请求未通过安全审核，任务已终止。",
        "events": [event],
    }
