"""API 请求与响应模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from graph.execution_options import ExecutionOptions


class GenerateRequest(BaseModel):
    user_request: str = Field(..., min_length=1, description="用户的短剧制作需求")
    job_id: str | None = Field(default=None, description="可选任务 ID；不传则自动生成")
    execution_options: ExecutionOptions | None = Field(default=None, description="节点执行开关")
    resume_from_checkpoint: bool = Field(
        default=False,
        description="是否从同一 job_id 的最后成功节点继续执行；前端重试按钮会设为 true",
    )
    force_restart: bool = Field(
        default=False,
        description="即使同一 job_id 已有 checkpoint，也从头重新执行。",
    )
    llm_format_mode: Literal["interrupt", "auto_repair"] = Field(
        default="interrupt",
        description=(
            "LLM 结构化输出失败策略："
            "interrupt=中断等待确认；auto_repair=确认后自动修复一次"
        ),
    )


class GenerateResponse(BaseModel):
    job_id: str
    status: str
    final_output_ready: bool
    final_message: str | None = None
    human_confirmation_required: bool = False
    human_confirmation_point: str | None = None
    human_questions: list[str] = Field(default_factory=list)
    editable_artifact_refs: dict[str, dict] = Field(default_factory=dict)
    resume_target_node: str | None = None
    llm_format_error: dict | None = None
    llm_repair_available: bool = False
    llm_runtime_error: dict | None = None
    llm_retry_available: bool = False
    checkpoint_found: bool = False
    resume_from_checkpoint: bool = False
    force_restart: bool = False
    completed_nodes: list[str] = Field(default_factory=list)
    last_completed_node: str | None = None
    execution_options: dict = Field(default_factory=dict)
    artifact_ids: dict[str, str] = Field(default_factory=dict)
    event_count: int = 0


class DirectorRunRequest(BaseModel):
    output_job_id: str | None = Field(
        default=None,
        description="可选模块运行任务 ID；不传则自动生成，避免覆盖源任务 checkpoint",
    )
    episode_script_artifact_id: str | None = Field(
        default=None,
        description="可选 episode_script artifact id；不传则使用源任务最新版本",
    )
    llm_format_mode: Literal["interrupt", "auto_repair"] = Field(
        default="interrupt",
        description="LLM 结构化输出失败策略",
    )


class AudiovisualRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_job_id: str | None = Field(
        default=None,
        description="可选模块运行任务 ID；不传则自动生成，避免覆盖源任务 checkpoint",
    )
    performance_direction_artifact_id: str | None = Field(
        default=None,
        description="可选 performance_direction artifact id；不传则使用源任务最新版本",
    )
    llm_format_mode: Literal["interrupt", "auto_repair"] = Field(
        default="interrupt",
        description="LLM 结构化输出失败策略",
    )


class ArtRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output_job_id: str | None = Field(
        default=None,
        description="可选模块运行任务 ID；不传则自动生成，避免覆盖源任务 checkpoint",
    )
    scene_breakdown_job_id: str | None = Field(
        default=None,
        description="可选 scene_breakdown 来源 job_id；不传则使用路径中的源任务 ID",
    )
    scene_breakdown_artifact_id: str | None = Field(
        default=None,
        description="可选 scene_breakdown artifact id；不传则使用来源任务最新版本",
    )
    audiovisual_enhanced_shot_list_job_id: str | None = Field(
        default=None,
        description="可选 audiovisual_enhanced_shot_list 来源 job_id；不传则使用路径中的源任务 ID",
    )
    audiovisual_enhanced_shot_list_artifact_id: str | None = Field(
        default=None,
        description="可选 audiovisual_enhanced_shot_list artifact id；不传则使用来源任务最新版本",
    )
    character_bible_job_id: str | None = Field(
        default=None,
        description="可选 character_bible 来源 job_id；不传则不加载",
    )
    character_bible_artifact_id: str | None = Field(
        default=None,
        description="可选 character_bible artifact id；不传则使用来源任务最新版本",
    )
    llm_format_mode: Literal["interrupt", "auto_repair"] = Field(
        default="interrupt",
        description="LLM 结构化输出失败策略",
    )


class ModuleRunResponse(BaseModel):
    job_id: str
    source_job_id: str
    module: str
    status: str
    module_output_ready: bool
    final_message: str | None = None
    human_confirmation_required: bool = False
    llm_format_error: dict | None = None
    llm_repair_available: bool = False
    llm_runtime_error: dict | None = None
    llm_retry_available: bool = False
    completed_nodes: list[str] = Field(default_factory=list)
    last_completed_node: str | None = None
    input_artifact_ids: dict[str, str] = Field(default_factory=dict)
    artifact_ids: dict[str, str] = Field(default_factory=dict)
    event_count: int = 0


class JobSummaryResponse(BaseModel):
    job_id: str
    exists: bool
    artifact_ids: dict[str, str] = Field(default_factory=dict)
    message: str | None = None


class JobRuntimeStatusResponse(BaseModel):
    job_id: str
    exists: bool = True
    status: str = "unknown"
    current_node: str | None = None
    current_stage: str | None = None
    started_at: str | None = None
    updated_at: str | None = None
    completed_nodes: list[str] = Field(default_factory=list)
    last_completed_node: str | None = None
    message: str | None = None
    artifact_ids: dict[str, str] = Field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None


class LLMPromptTraceSummary(BaseModel):
    trace_id: str
    job_id: str
    created_at: str | None = None
    prompt_id: str | None = None
    prompt_version: int | str | None = None
    path: str
    message_count: int = 0
    message_summary: list[dict] = Field(default_factory=list)


class LLMPromptTraceListResponse(BaseModel):
    job_id: str
    prompts: list[LLMPromptTraceSummary] = Field(default_factory=list)


class LLMPromptTraceDetailResponse(BaseModel):
    trace_id: str
    job_id: str
    created_at: str | None = None
    prompt_id: str | None = None
    prompt_version: int | str | None = None
    path: str
    model_requested: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    response_format: dict | None = None
    variables_summary: dict = Field(default_factory=dict)
    message_summary: list[dict] = Field(default_factory=list)
    messages: list[dict] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ArtifactContentResponse(BaseModel):
    job_id: str
    artifact_key: str
    artifact_id: str
    artifact_type: str
    version: int
    content: dict | list | str | int | float | bool | None


class HumanConfirmationSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_point: Literal["brief", "style", "episode_outline"] | None = Field(
        default=None,
        description="确认点；不传则使用 checkpoint 中当前暂停点。",
    )
    action: Literal["approve", "revise"]
    mode: Literal["normal", "expert"] = Field(
        default="normal",
        description="normal=自然语言修改；expert=直接提交 artifact JSON。",
    )
    feedback: str | None = Field(default=None, description="普通模式下的自然语言修改意见。")
    artifact_content: dict | list | None = Field(
        default=None,
        description="专家模式下提交的结构化 artifact 内容。",
    )
    llm_format_mode: Literal["interrupt", "auto_repair"] = Field(
        default="interrupt",
        description="普通模式调用 LLM 修订时的结构化输出失败策略。",
    )
    resume_after_approve: bool = Field(default=True, description="确认通过后是否自动继续流程。")


class HumanConfirmationResponse(BaseModel):
    job_id: str
    status: str
    final_output_ready: bool = False
    final_message: str | None = None
    human_confirmation_required: bool = False
    human_confirmation_point: str | None = None
    human_questions: list[str] = Field(default_factory=list)
    editable_artifact_refs: dict[str, dict] = Field(default_factory=dict)
    resume_target_node: str | None = None
    revised_artifact_key: str | None = None
    revised_artifact_id: str | None = None
    llm_format_error: dict | None = None
    llm_repair_available: bool = False
    llm_runtime_error: dict | None = None
    llm_retry_available: bool = False
    resume_from_checkpoint: bool = False
    completed_nodes: list[str] = Field(default_factory=list)
    last_completed_node: str | None = None
    execution_options: dict = Field(default_factory=dict)
    artifact_ids: dict[str, str] = Field(default_factory=dict)
    event_count: int = 0
