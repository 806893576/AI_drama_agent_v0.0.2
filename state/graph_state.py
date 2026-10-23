"""LangGraph 轻量状态定义占位。

后续应定义 DramaGraphState，保存 current_stage、next_node、artifact_refs、review_status、
revision_counters、producer_decision、user_feedback 和运行错误等轻量信息。
"""

# 作用：定义整个 LangGraph 运行时 state 的结构。
from typing import Annotated, Any, TypedDict

from domain.brief.schemas import BriefValidation, CreativeBrief
from domain.brief.validators import BriefGateResult
from domain.review.repair_plan import RepairPlan
from domain.review.safety_review import SafetyReviewReport
from schemas.enums import NodeId, StageId
from state.artifact_refs import ArtifactRef
from state.events import RuntimeEvent
from state.producer_decision import ProducerDecision
from state.reducers import append_events, merge_artifact_refs, merge_retry_counts


# 这是 StateGraph(DramaGraphState) 的基础。每个节点读取 state，并返回局部更新。
class DramaGraphState(TypedDict, total=False):
    job_id: str
    user_request: str
    execution_options: dict[str, Any] | Any

    current_stage: StageId
    next_node: NodeId | None

    artifact_refs: Annotated[dict[str, ArtifactRef], merge_artifact_refs]
    asset_registry_ref: ArtifactRef | None
    last_review_ref: ArtifactRef | None

    producer_decision: ProducerDecision | None
    repair_plan: RepairPlan | None

    retry_counts: Annotated[dict[str, int], merge_retry_counts]
    user_feedback: list[dict]
    events: Annotated[list[RuntimeEvent], append_events]

    error: str | None

    # Step 10: input safety MVP transient fields
    input_safety_report: SafetyReviewReport | None

    # Step 11: brief agent MVP transient fields
    creative_brief: CreativeBrief | None
    brief_validation: BriefValidation | None

    # Step 12: brief gate MVP transient fields
    brief_gate_result: BriefGateResult | None

    # 风格指南：由 brief 后的 style_guide 节点生成，供编剧、导演、视听、美术和审核复用。
    style_guide: Any
    style_guide_summary: str

    # Step 14: skeleton graph terminal/pause fields
    human_confirmation_required: bool
    human_confirmation_point: str | None
    confirmed_human_points: list[str]
    editable_artifact_refs: dict[str, Any]
    resume_target_node: str | None
    human_questions: list[str]
    terminated: bool
    final_message: str | None
    writer_stub_completed: bool
    final_output_ready: bool
    completed_nodes: list[str]
    last_completed_node: str | None
    resume_mode: bool
    resume_from_checkpoint: bool

    # 编剧阶段的结构化中间结果。长文本仍会保存到 Artifact Store，
    # 这里保留轻量对象，方便 MVP 阶段的下游节点直接消费。
    story_bible: Any
    story_synopsis: Any
    character_bible: Any
    episode_outline_package: Any
    episode_scripts: list[Any]
    dialogue_polish_package: Any
    writer_package: dict[str, Any]
    writer_subgraph_completed: bool

    # 审核、返工、导演、视听、美术、资产与终审阶段的运行态字段。
    script_review_report: Any
    quality_score_report: Any
    script_safety_report: Any
    text_continuity_report: Any
    scene_breakdowns: list[Any]
    shot_designs: list[Any]
    performance_direction: list[Any]
    audiovisual_enhanced_shot_list: list[Any]
    director_package: dict[str, Any]
    audiovisual_package: dict[str, Any]
    shot_av_safety_report: Any
    art_prompt_package: Any
    prompt_safety_report: Any
    asset_registry: Any
    production_continuity_report: Any
    final_safety_report: Any
    final_acceptance_report: dict[str, Any]
    final_package: dict[str, Any]
