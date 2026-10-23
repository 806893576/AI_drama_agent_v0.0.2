from uuid import uuid4

from fastapi.testclient import TestClient

import api.routes as api_routes
import services.human_confirmation as human_confirmation_service
from api.routes import (
    create_art_run,
    create_audiovisual_run,
    create_director_run,
    create_generation_job,
    get_job,
    get_job_artifact,
    get_job_llm_prompt,
    get_job_runtime,
    list_job_llm_prompts,
    submit_human_confirmation,
)
from api.schemas import (
    ArtRunRequest,
    AudiovisualRunRequest,
    DirectorRunRequest,
    GenerateRequest,
    HumanConfirmationSubmitRequest,
)
from api.server import create_app
from memory.checkpoint import JsonCheckpointStore
from services.llm import LLMTraceStore, llm_trace_context
from services.llm.models import LLMMessage
from workflows.generation_workflow import WorkflowRunResult


def test_api_create_generation_job_and_query() -> None:
    response = create_generation_job(
        GenerateRequest(
            job_id="job_api_001",
            user_request="都市逆袭短剧，平台抖音，12集，每集2分钟，女主夺回公司。",
        )
    )

    assert response.final_output_ready is True
    assert "final_package" in response.artifact_ids

    job = get_job("job_api_001")

    assert job.exists is True
    assert "final_package" in job.artifact_ids


def test_api_root_page_contains_execution_options() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "节点执行开关" in response.text
    assert "run_script_review" in response.text
    assert "run_final_acceptance" in response.text
    assert "确认 LLM 修复并重新运行" in response.text
    assert "llm_format_mode" in response.text
    assert "resume_from_checkpoint" in response.text
    assert "从失败节点重试" in response.text
    assert "LLM Prompt Trace" in response.text
    assert "模块单独运行" in response.text
    assert "只运行导演模块" in response.text
    assert "只运行视听模块" in response.text
    assert "运行状态" in response.text
    assert "当前节点" in response.text
    assert "人工确认节点" in response.text


def test_api_job_accepts_execution_options() -> None:
    response = create_generation_job(
        GenerateRequest(
            job_id="job_api_fast_options_001",
            user_request="都市逆袭短剧，平台抖音，12集，每集2分钟，女主夺回公司。",
            execution_options={
                "run_script_review": False,
                "run_quality_scoring": False,
                "run_script_safety": False,
                "run_text_continuity": False,
                "run_shot_av_safety": False,
                "run_prompt_safety": False,
                "run_production_continuity": False,
                "run_final_safety": False,
                "run_final_acceptance": False,
            },
        )
    )

    assert response.final_output_ready is True
    assert "final_package" in response.artifact_ids
    assert "script_review" not in response.artifact_ids
    assert response.execution_options["run_script_review"] is False


def test_api_auto_resumes_existing_job_checkpoint(monkeypatch) -> None:
    job_id = "job_api_auto_resume_001"
    JsonCheckpointStore().save(
        job_id,
        {
            "job_id": job_id,
            "user_request": "旧请求",
            "execution_options": {"run_script_review": False},
            "completed_nodes": ["writer.episode_script"],
        },
    )
    captured: dict[str, object] = {}

    def fake_run_generation(*args, **kwargs) -> WorkflowRunResult:
        captured.update(kwargs)
        return WorkflowRunResult(
            state={},
            summary={
                "job_id": kwargs["job_id"],
                "final_output_ready": True,
                "resume_from_checkpoint": kwargs["resume_from_checkpoint"],
                "artifact_ids": {"final_package": "final_package_v001"},
                "completed_nodes": ["writer.episode_script", "final_output"],
            },
        )

    monkeypatch.setattr(api_routes, "run_generation", fake_run_generation)

    response = create_generation_job(
        GenerateRequest(
            job_id=job_id,
            user_request="继续这个任务",
        )
    )

    assert captured["resume_from_checkpoint"] is True
    assert response.checkpoint_found is True
    assert response.resume_from_checkpoint is True


def test_api_can_force_restart_existing_job_checkpoint(monkeypatch) -> None:
    job_id = "job_api_force_restart_001"
    JsonCheckpointStore().save(
        job_id,
        {
            "job_id": job_id,
            "user_request": "旧请求",
            "execution_options": {"run_script_review": False},
            "completed_nodes": ["writer.episode_script"],
        },
    )
    captured: dict[str, object] = {}

    def fake_run_generation(*args, **kwargs) -> WorkflowRunResult:
        captured.update(kwargs)
        return WorkflowRunResult(
            state={},
            summary={
                "job_id": kwargs["job_id"],
                "final_output_ready": True,
                "resume_from_checkpoint": kwargs["resume_from_checkpoint"],
                "artifact_ids": {"final_package": "final_package_v001"},
                "completed_nodes": ["input_safety", "final_output"],
            },
        )

    monkeypatch.setattr(api_routes, "run_generation", fake_run_generation)

    response = create_generation_job(
        GenerateRequest(
            job_id=job_id,
            user_request="重跑这个任务",
            force_restart=True,
        )
    )

    assert captured["resume_from_checkpoint"] is False
    assert response.checkpoint_found is True
    assert response.force_restart is True


def test_api_lists_and_reads_llm_prompt_traces() -> None:
    with llm_trace_context("job_api_prompt_trace_001"):
        prompt_path = LLMTraceStore().save_prompt(
            {
                "trace_id": "trace_api_prompt_001",
                "prompt_id": "writer.episode_script",
                "prompt_version": 3,
                "messages": [
                    LLMMessage(role="system", content="系统提示"),
                    LLMMessage(role="user", content="用户提示"),
                ],
            }
        )

    listing = list_job_llm_prompts("job_api_prompt_trace_001")

    assert len(listing.prompts) == 1
    assert listing.prompts[0].trace_id == "trace_api_prompt_001"
    assert listing.prompts[0].path == str(prompt_path)

    detail = get_job_llm_prompt("job_api_prompt_trace_001", "trace_api_prompt_001")

    assert detail.prompt_id == "writer.episode_script"
    assert detail.messages[0]["content"] == "系统提示"
    assert detail.messages[1]["content"] == "用户提示"


def test_api_runs_director_and_audiovisual_modules_from_artifacts() -> None:
    source = create_generation_job(
        GenerateRequest(
            job_id="job_api_module_source_001",
            user_request="都市逆袭短剧，平台抖音，12集，每集2分钟，女主夺回公司。",
        )
    )

    director = create_director_run(
        "job_api_module_source_001",
        DirectorRunRequest(output_job_id="job_api_director_module_001"),
    )

    assert director.source_job_id == "job_api_module_source_001"
    assert director.job_id == "job_api_director_module_001"
    assert director.module == "director"
    assert director.module_output_ready is True
    assert director.input_artifact_ids["episode_script"] == source.artifact_ids["episode_script"]
    assert "director_package" in director.artifact_ids
    assert "scene_breakdown" in director.artifact_ids
    assert "shot_list" in director.artifact_ids
    assert "performance_direction" in director.artifact_ids

    audiovisual = create_audiovisual_run(
        "job_api_director_module_001",
        AudiovisualRunRequest(output_job_id="job_api_av_module_001"),
    )

    assert audiovisual.source_job_id == "job_api_director_module_001"
    assert audiovisual.job_id == "job_api_av_module_001"
    assert audiovisual.module == "audiovisual"
    assert audiovisual.module_output_ready is True
    assert (
        audiovisual.input_artifact_ids["performance_direction"]
        == director.artifact_ids["performance_direction"]
    )
    assert "scene_breakdown" not in audiovisual.input_artifact_ids
    assert "shot_list" not in audiovisual.input_artifact_ids
    assert "audiovisual_enhanced_shot_list" in audiovisual.artifact_ids
    assert "audiovisual_package" in audiovisual.artifact_ids

    art = create_art_run(
        "job_api_av_module_001",
        ArtRunRequest(
            output_job_id="job_api_art_module_001",
            scene_breakdown_job_id="job_api_director_module_001",
            audiovisual_enhanced_shot_list_job_id="job_api_av_module_001",
        ),
    )

    assert art.source_job_id == "job_api_av_module_001"
    assert art.job_id == "job_api_art_module_001"
    assert art.module == "art"
    assert art.module_output_ready is True
    assert art.input_artifact_ids["scene_breakdown"] == director.artifact_ids["scene_breakdown"]
    assert (
        art.input_artifact_ids["audiovisual_enhanced_shot_list"]
        == audiovisual.artifact_ids["audiovisual_enhanced_shot_list"]
    )
    assert "art_package" in art.artifact_ids


def test_api_rejects_legacy_audiovisual_module_inputs() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/jobs/job_api_module_source_001/audiovisual-runs",
        json={
            "scene_breakdown_artifact_id": "scene_breakdown_v001",
            "shot_list_artifact_id": "shot_list_v001",
        },
    )

    assert response.status_code == 422
    assert "extra_forbidden" in response.text


def test_api_exposes_runtime_status_after_job_run() -> None:
    response = create_generation_job(
        GenerateRequest(
            job_id="job_api_runtime_status_001",
            user_request="都市逆袭短剧，平台抖音，12集，每集2分钟，女主夺回公司。",
        )
    )

    status = get_job_runtime("job_api_runtime_status_001")

    assert status.exists is True
    assert status.job_id == "job_api_runtime_status_001"
    assert status.last_completed_node == "final_output"
    assert status.current_node is None
    assert "final_package" in status.artifact_ids
    assert len(status.completed_nodes) == len(response.completed_nodes)


def test_api_human_confirmation_normal_revision_and_approval_flow() -> None:
    job_id = f"job_api_human_{uuid4().hex[:8]}"
    response = create_generation_job(
        GenerateRequest(
            job_id=job_id,
            user_request="都市逆袭短剧，平台抖音，3集，每集2分钟，女主夺回公司。",
            execution_options={"enable_human_confirmations": True},
        )
    )

    assert response.human_confirmation_required is True
    assert response.human_confirmation_point == "brief"

    artifact = get_job_artifact(job_id, "creative_brief")
    assert artifact.artifact_key == "creative_brief"

    revised = submit_human_confirmation(
        job_id,
        HumanConfirmationSubmitRequest(
            action="revise",
            mode="normal",
            feedback="故事方向更偏校园创业，保留女主夺回主动权。",
            resume_after_approve=False,
        ),
    )

    assert revised.human_confirmation_required is True
    assert revised.human_confirmation_point == "brief"
    assert revised.revised_artifact_key == "creative_brief"
    assert revised.revised_artifact_id

    approved_brief = submit_human_confirmation(
        job_id,
        HumanConfirmationSubmitRequest(action="approve"),
    )

    assert approved_brief.human_confirmation_required is True
    assert approved_brief.human_confirmation_point == "style"

    approved_style = submit_human_confirmation(
        job_id,
        HumanConfirmationSubmitRequest(action="approve"),
    )

    assert approved_style.human_confirmation_required is True
    assert approved_style.human_confirmation_point == "episode_outline"

    completed = submit_human_confirmation(
        job_id,
        HumanConfirmationSubmitRequest(action="approve"),
    )

    assert completed.final_output_ready is True
    assert completed.human_confirmation_required is False
    assert "final_package" in completed.artifact_ids


def test_api_human_confirmation_expert_revision_saves_json() -> None:
    job_id = f"job_api_human_expert_{uuid4().hex[:8]}"
    create_generation_job(
        GenerateRequest(
            job_id=job_id,
            user_request="都市逆袭短剧，平台抖音，3集，每集2分钟，赛璐璐美术风格。",
            execution_options={"enable_human_confirmations": True},
        )
    )
    submit_human_confirmation(job_id, HumanConfirmationSubmitRequest(action="approve"))
    style_artifact = get_job_artifact(job_id, "style_guide")
    content = dict(style_artifact.content)
    content["style_do"] = f"{content.get('style_do', '')}；人工确认：画面更明亮。"

    revised = submit_human_confirmation(
        job_id,
        HumanConfirmationSubmitRequest(
            action="revise",
            mode="expert",
            confirmation_point="style",
            artifact_content=content,
        ),
    )

    assert revised.human_confirmation_required is True
    assert revised.human_confirmation_point == "style"
    assert revised.revised_artifact_key == "style_guide"
    saved = get_job_artifact(job_id, "style_guide")
    assert "画面更明亮" in saved.content["style_do"]


def test_episode_outline_normal_revision_uses_compact_context(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_generate_model_with_fallback(prompt_id, variables, model_type, fallback, **kwargs):
        if prompt_id == "human_revision.episode_outline":
            captured["variables"] = variables
            captured["model_type"] = model_type
        return fallback()

    monkeypatch.setattr(
        human_confirmation_service,
        "generate_model_with_fallback",
        fake_generate_model_with_fallback,
    )
    job_id = f"job_api_human_outline_compact_{uuid4().hex[:8]}"
    create_generation_job(
        GenerateRequest(
            job_id=job_id,
            user_request="都市逆袭短剧，平台抖音，5集，每集2分钟，女主夺回公司。",
            execution_options={"enable_human_confirmations": True},
        )
    )
    submit_human_confirmation(job_id, HumanConfirmationSubmitRequest(action="approve"))
    submit_human_confirmation(job_id, HumanConfirmationSubmitRequest(action="approve"))

    revised = submit_human_confirmation(
        job_id,
        HumanConfirmationSubmitRequest(
            action="revise",
            mode="normal",
            confirmation_point="episode_outline",
            feedback="第2集结尾增加女主发现闺蜜背叛的反转。",
        ),
    )

    variables = captured["variables"]
    assert revised.human_confirmation_point == "episode_outline"
    assert variables["guardrails"].count("Story Bible") == 0
    assert "story_bible_id" not in variables["guardrails"]
    assert "character_bible_id" not in variables["guardrails"]
    assert '"episode_number": 2' in variables["current_artifact"]
    assert '"episode_number": 4' not in variables["current_artifact"]
    assert "第2集" in variables["context_summary"]
    assert "第4集" not in variables["context_summary"]
