"""功能：通用 Agent 节点，封装单个 Agent 在 LangGraph 中的执行适配逻辑。"""

# 作用：把 Brief Agent 包装成 LangGraph node 风格函数。
from agents.brief_agent import analyze_brief
from schemas.enums import ArtifactType, EventStatus, NodeId, StageId
from services.storage.artifact_store import ArtifactStore
from state.events import RuntimeEvent

"""
这里暂时把完整 creative_brief 和 brief_validation 放回 state，是为了测试和路由方便。
后续接入 Artifact Store 后，应只保存 ref。
MVP 阶段可以先保留：
    "creative_brief": result.creative_brief
    "brief_validation": result.validation
"""
"""
作用：将 BriefAgent 包装成符合 LangGraph 规范的节点（Node）函数。
核心逻辑：
从全局 state 中提取 job_id 和 user_request。
    调用 analyze_brief 解析用户的自然语言需求。
    创建对应的产物引用（ArtifactRef），分别为 creative_brief（创作简报引用）
    和 brief_validation（完整性校验引用），并绑定创建者为 NodeId.BRIEF_AGENT。
    生成一个 RuntimeEvent 运行时事件，记录该节点执行成功（COMPLETED）。
    返回包含当前阶段更新、产物引用字典、原始结构化简报数据、校验结果以及事件日志的字典，供工作流图状态合并。
"""
def brief_agent_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    user_request = state.get("user_request", "")

    """
    result = class BriefAnalysisResult(BaseModel):
        creative_brief: CreativeBrief
        validation: BriefValidation
    """
    result = analyze_brief(user_request)
    store = ArtifactStore()

    brief_ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.CREATIVE_BRIEF,
        content=result.creative_brief,
        summary="结构化创作简报。",
        created_by=NodeId.BRIEF_AGENT,
    )

    validation_ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.BRIEF_VALIDATION,
        content=result.validation,
        summary="创作简报完整性校验结果。",
        created_by=NodeId.BRIEF_AGENT,
        parent_ref=brief_ref,
    )

    event = RuntimeEvent(
        event_id=f"{job_id}_brief_agent_completed",
        node_id=NodeId.BRIEF_AGENT,
        stage=StageId.BRIEF,
        status=EventStatus.COMPLETED,
        message="Creative brief analysis completed.",
        artifact_ids=[brief_ref.artifact_id, validation_ref.artifact_id],
    )

    return {
        "current_stage": StageId.BRIEF,
        "artifact_refs": {
            "creative_brief": brief_ref,
            "brief_validation": validation_ref,
        },
        "creative_brief": result.creative_brief,
        "brief_validation": result.validation,
        "events": [event],
    }
