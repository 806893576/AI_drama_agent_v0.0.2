from graph.execution_options import ExecutionOptions
from workflows.generation_workflow import run_generation


def test_fast_draft_skips_review_and_safety_nodes() -> None:
    result = run_generation(
        "都市逆袭短剧，平台抖音，12集，每集2分钟，风格强爽点、快节奏，女主夺回主动权。",
        job_id="job_fast_draft_001",
        execution_options=ExecutionOptions.fast_draft(),
    )

    artifact_ids = result.summary["artifact_ids"]

    assert result.summary["final_output_ready"] is True
    assert "writer_package" in artifact_ids
    assert "director_package" in artifact_ids
    assert "audiovisual_package" in artifact_ids
    assert "art_package" in artifact_ids
    assert "asset_registry" in artifact_ids
    assert "final_package" in artifact_ids

    assert "script_review" not in artifact_ids
    assert "quality_score" not in artifact_ids
    assert "script_safety_report" not in artifact_ids
    assert "text_continuity_report" not in artifact_ids
    assert "shot_av_safety_report" not in artifact_ids
    assert "prompt_safety_report" not in artifact_ids
    assert "production_continuity_report" not in artifact_ids
    assert "final_safety_report" not in artifact_ids
    assert result.summary["execution_options"]["skipped_reason"] == "fast_draft"


def test_can_skip_only_script_review_but_keep_quality_and_safety() -> None:
    result = run_generation(
        "都市逆袭短剧，平台抖音，12集，每集2分钟，风格强爽点、快节奏，女主夺回主动权。",
        job_id="job_skip_script_review_001",
        execution_options={"run_script_review": False},
    )

    artifact_ids = result.summary["artifact_ids"]

    assert result.summary["final_output_ready"] is True
    assert "script_review" not in artifact_ids
    assert "quality_score" in artifact_ids
    assert "script_safety_report" in artifact_ids
    assert "final_package" in artifact_ids
