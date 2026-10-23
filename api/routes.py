"""FastAPI 路由。"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from api.schemas import (
    ArtifactContentResponse,
    ArtRunRequest,
    AudiovisualRunRequest,
    DirectorRunRequest,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    HumanConfirmationResponse,
    HumanConfirmationSubmitRequest,
    JobRuntimeStatusResponse,
    JobSummaryResponse,
    LLMPromptTraceDetailResponse,
    LLMPromptTraceListResponse,
    LLMPromptTraceSummary,
    ModuleRunResponse,
)
from core.settings import get_settings
from database.connection import JsonDatabase
from memory.checkpoint import JsonCheckpointStore
from services.human_confirmation import (
    approve_human_confirmation,
    load_editable_artifact,
    revise_human_confirmation,
)
from services.llm import LLMTraceStore
from services.runtime_status import get_job_runtime_status
from workflows.generation_workflow import run_generation, summarize_graph_result, to_jsonable
from workflows.module_workflow import (
    run_art_generation,
    run_audiovisual_generation,
    run_director_generation,
)

router = APIRouter(prefix="/api/v1", tags=["drama-generation"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, version=settings.app_version)


@router.post("/jobs", response_model=GenerateResponse)
def create_generation_job(payload: GenerateRequest) -> GenerateResponse:
    job_id = payload.job_id or f"job_{uuid4().hex[:12]}"
    checkpoint_found = JsonCheckpointStore().exists(job_id)
    should_resume = (
        not payload.force_restart
        and checkpoint_found
        and (payload.resume_from_checkpoint or payload.job_id is not None)
    )
    result = run_generation(
        payload.user_request,
        job_id=job_id,
        execution_options=payload.execution_options,
        llm_format_mode=payload.llm_format_mode,
        resume_from_checkpoint=should_resume,
    )
    summary = result.summary
    return GenerateResponse(
        job_id=job_id,
        status="completed" if summary.get("final_output_ready") else "paused_or_rejected",
        final_output_ready=summary.get("final_output_ready", False),
        final_message=summary.get("final_message"),
        human_confirmation_required=summary.get("human_confirmation_required", False),
        human_confirmation_point=summary.get("human_confirmation_point"),
        human_questions=summary.get("human_questions", []),
        editable_artifact_refs=summary.get("editable_artifact_refs", {}),
        resume_target_node=summary.get("resume_target_node"),
        llm_format_error=summary.get("llm_format_error"),
        llm_repair_available=summary.get("llm_repair_available", False),
        llm_runtime_error=summary.get("llm_runtime_error"),
        llm_retry_available=summary.get("llm_retry_available", False),
        checkpoint_found=checkpoint_found,
        resume_from_checkpoint=summary.get("resume_from_checkpoint", False),
        force_restart=payload.force_restart,
        completed_nodes=summary.get("completed_nodes", []),
        last_completed_node=summary.get("last_completed_node"),
        execution_options=summary.get("execution_options", {}),
        artifact_ids=summary.get("artifact_ids", {}),
        event_count=summary.get("event_count", 0),
    )


@router.get("/jobs/{job_id}/artifacts/{artifact_key}", response_model=ArtifactContentResponse)
def get_job_artifact(job_id: str, artifact_key: str) -> ArtifactContentResponse:
    try:
        artifact = load_editable_artifact(job_id, artifact_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ArtifactContentResponse(
        job_id=job_id,
        artifact_key=artifact.artifact_key,
        artifact_id=artifact.ref.artifact_id,
        artifact_type=artifact.ref.artifact_type.value,
        version=artifact.ref.version,
        content=to_jsonable(artifact.content),
    )


@router.post(
    "/jobs/{job_id}/human-confirmations",
    response_model=HumanConfirmationResponse,
)
def submit_human_confirmation(
    job_id: str,
    payload: HumanConfirmationSubmitRequest,
) -> HumanConfirmationResponse:
    try:
        if payload.action == "approve":
            update = approve_human_confirmation(
                job_id,
                confirmation_point=payload.confirmation_point,
            )
            if payload.resume_after_approve:
                result = run_generation(
                    update.state.get("user_request", ""),
                    job_id=job_id,
                    execution_options=update.state.get("execution_options"),
                    llm_format_mode=payload.llm_format_mode,
                    resume_from_checkpoint=True,
                )
                return _human_confirmation_response_from_summary(
                    job_id=job_id,
                    summary=result.summary,
                    message=result.summary.get("final_message"),
                )
            summary = summarize_graph_result(update.state)
            return _human_confirmation_response_from_summary(
                job_id=job_id,
                summary=summary,
                message=update.message,
            )

        update = revise_human_confirmation(
            job_id,
            confirmation_point=payload.confirmation_point,
            mode=payload.mode,
            feedback=payload.feedback,
            artifact_content=payload.artifact_content,
            llm_format_mode=payload.llm_format_mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    summary = summarize_graph_result(update.state)
    return _human_confirmation_response_from_summary(
        job_id=job_id,
        summary=summary,
        message=update.message,
        revised_artifact_key=update.revised_artifact_key,
        revised_artifact_id=update.revised_artifact_id,
    )


@router.post("/jobs/{job_id}/director-runs", response_model=ModuleRunResponse)
def create_director_run(job_id: str, payload: DirectorRunRequest) -> ModuleRunResponse:
    try:
        result = run_director_generation(
            source_job_id=job_id,
            output_job_id=payload.output_job_id,
            episode_script_artifact_id=payload.episode_script_artifact_id,
            llm_format_mode=payload.llm_format_mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ModuleRunResponse(**result.summary)


@router.post("/jobs/{job_id}/audiovisual-runs", response_model=ModuleRunResponse)
def create_audiovisual_run(
    job_id: str,
    payload: AudiovisualRunRequest,
) -> ModuleRunResponse:
    try:
        result = run_audiovisual_generation(
            source_job_id=job_id,
            output_job_id=payload.output_job_id,
            performance_direction_artifact_id=payload.performance_direction_artifact_id,
            llm_format_mode=payload.llm_format_mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ModuleRunResponse(**result.summary)


@router.post("/jobs/{job_id}/art-runs", response_model=ModuleRunResponse)
def create_art_run(job_id: str, payload: ArtRunRequest) -> ModuleRunResponse:
    try:
        result = run_art_generation(
            source_job_id=job_id,
            output_job_id=payload.output_job_id,
            scene_breakdown_job_id=payload.scene_breakdown_job_id,
            scene_breakdown_artifact_id=payload.scene_breakdown_artifact_id,
            audiovisual_enhanced_shot_list_job_id=(
                payload.audiovisual_enhanced_shot_list_job_id
            ),
            audiovisual_enhanced_shot_list_artifact_id=(
                payload.audiovisual_enhanced_shot_list_artifact_id
            ),
            character_bible_job_id=payload.character_bible_job_id,
            character_bible_artifact_id=payload.character_bible_artifact_id,
            llm_format_mode=payload.llm_format_mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ModuleRunResponse(**result.summary)


@router.get("/jobs/{job_id}", response_model=JobSummaryResponse)
def get_job(job_id: str) -> JobSummaryResponse:
    db = JsonDatabase()
    record = db.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return JobSummaryResponse(
        job_id=job_id,
        exists=True,
        artifact_ids=record.artifact_ids,
        message=record.final_message,
    )


@router.get("/jobs/{job_id}/runtime-status", response_model=JobRuntimeStatusResponse)
def get_job_runtime(job_id: str) -> JobRuntimeStatusResponse:
    status = get_job_runtime_status(job_id)
    if status is not None:
        return JobRuntimeStatusResponse(**status)

    record = JsonDatabase().get_job(job_id)
    if record is None:
        return JobRuntimeStatusResponse(job_id=job_id, exists=False)
    return JobRuntimeStatusResponse(
        job_id=job_id,
        status=record.status,
        message=record.final_message,
        artifact_ids=record.artifact_ids,
        updated_at=record.updated_at.isoformat(),
    )


@router.get("/jobs/{job_id}/llm-prompts", response_model=LLMPromptTraceListResponse)
def list_job_llm_prompts(job_id: str) -> LLMPromptTraceListResponse:
    prompts = [LLMPromptTraceSummary(**item) for item in LLMTraceStore().list_prompts(job_id)]
    if not prompts and JsonDatabase().get_job(job_id) is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return LLMPromptTraceListResponse(job_id=job_id, prompts=prompts)


@router.get(
    "/jobs/{job_id}/llm-prompts/{trace_id}",
    response_model=LLMPromptTraceDetailResponse,
)
def get_job_llm_prompt(job_id: str, trace_id: str) -> LLMPromptTraceDetailResponse:
    prompt = LLMTraceStore().load_prompt(job_id, trace_id)
    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail=f"LLM prompt trace not found: {job_id}/{trace_id}",
        )
    return LLMPromptTraceDetailResponse(**prompt)


def _human_confirmation_response_from_summary(
    *,
    job_id: str,
    summary: dict,
    message: str | None = None,
    revised_artifact_key: str | None = None,
    revised_artifact_id: str | None = None,
) -> HumanConfirmationResponse:
    return HumanConfirmationResponse(
        job_id=job_id,
        status="completed" if summary.get("final_output_ready") else "paused_or_rejected",
        final_output_ready=summary.get("final_output_ready", False),
        final_message=message if message is not None else summary.get("final_message"),
        human_confirmation_required=summary.get("human_confirmation_required", False),
        human_confirmation_point=summary.get("human_confirmation_point"),
        human_questions=summary.get("human_questions", []),
        editable_artifact_refs=summary.get("editable_artifact_refs", {}),
        resume_target_node=summary.get("resume_target_node"),
        revised_artifact_key=revised_artifact_key,
        revised_artifact_id=revised_artifact_id,
        llm_format_error=summary.get("llm_format_error"),
        llm_repair_available=summary.get("llm_repair_available", False),
        llm_runtime_error=summary.get("llm_runtime_error"),
        llm_retry_available=summary.get("llm_retry_available", False),
        resume_from_checkpoint=summary.get("resume_from_checkpoint", False),
        completed_nodes=summary.get("completed_nodes", []),
        last_completed_node=summary.get("last_completed_node"),
        execution_options=summary.get("execution_options", {}),
        artifact_ids=summary.get("artifact_ids", {}),
        event_count=summary.get("event_count", 0),
    )
