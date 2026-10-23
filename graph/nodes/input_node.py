"""用户输入节点占位。

负责接收原始用户请求，写入 Graph State 的 user_request，并触发输入安全检查。
"""

from schemas.enums import ArtifactType, EventStatus, NodeId, StageId
from state.artifact_refs import ArtifactRef
from state.events import RuntimeEvent
from safety.input_guard import check_user_request


# 作用：把纯安全审核器包装成 LangGraph node 风格的函数。
# 这里临时把完整 input_safety_report 放回 state，是为了测试路由方便。严格来说，未来应该把报告保存进 Artifact Store，只把 review_ref 放进 state。
"""
你可以选择两种方式：
MVP 简化版：
    "input_safety_report": report
方便测试。

严格分层版：
后续接 Artifact Store 后移除这行，只保存：
    "last_review_ref": review_ref
目前建议先保留，等主图接 Artifact Store 时再清理。
"""
# 在 LangGraph 中，你之所以只需要在函数参数里接收一个简单的 state: dict（或者具体的 TypedDict 类型），就能实现对全局系统状态的更新
def input_safety_node(state: dict) -> dict:
    """Run input safety review and return a partial state update."""
    job_id = state.get("job_id", "job_unknown")
    user_request = state.get("user_request", "")

    report = check_user_request(user_request)

    # 实例化一个 ArtifactRef（产物引用对象），用来记录这次输入安全审核报告的元数据（版本、创建者等）
    review_ref = ArtifactRef(
        artifact_id="input_safety_v001",
        artifact_type=ArtifactType.SAFETY_REVIEW,
        version=1,
        summary="输入安全审核报告。",
        created_by=NodeId.INPUT_SAFETY,
    )

    # 创建一个 RuntimeEvent（运行时事件日志），记录该节点执行完成的详细信息
    event = RuntimeEvent(
        event_id=f"{job_id}_input_safety_completed",
        node_id=NodeId.INPUT_SAFETY,
        stage=StageId.SAFETY,
        status=EventStatus.COMPLETED,
        message="Input safety review completed.",
        artifact_ids=[review_ref.artifact_id],
    )

    return {
        "current_stage": StageId.SAFETY,
        "last_review_ref": review_ref,
        "input_safety_report": report,
        "events": [event],
    }