from graph.builder import build_drama_graph
from services.storage.artifact_store import ArtifactStore


def test_full_v4_workflow_generates_production_package() -> None:
    graph = build_drama_graph()

    result = graph.invoke(
        {
            "job_id": "job_full_v4_001",
            "user_request": (
                "都市逆袭短剧，平台抖音，12集，每集2分钟，"
                "女主被夺走公司后重新夺回主动权。"
            ),
        }
    )

    artifact_refs = result["artifact_refs"]

    assert result["final_output_ready"] is True
    assert result["writer_subgraph_completed"] is True
    assert result["script_review_report"].passed is True
    assert result["quality_score_report"].passed is True
    assert result["script_safety_report"].passed is True
    assert result["text_continuity_report"].passed is True
    assert result["shot_av_safety_report"].passed is True
    assert result["prompt_safety_report"].passed is True
    assert result["production_continuity_report"].passed is True
    assert result["final_safety_report"].passed is True
    assert result["final_acceptance_report"]["passed"] is True

    assert result["scene_breakdowns"]
    assert result["shot_designs"]
    assert result["audiovisual_package"]
    assert result["art_prompt_package"].asset_prompts.character_assets
    assert result["art_prompt_package"].asset_prompts.scene_assets
    assert result["art_prompt_package"].shot_prompt_plan
    assert result["asset_registry"].characters
    assert result["asset_registry"].scenes
    assert result["asset_registry"].shots
    assert result["asset_registry"].prompts

    final_package = result["final_package"]
    assert final_package["source_artifact_ids"]["art_package"].startswith("art_package_v")
    assert final_package["source_artifact_ids"][
        "audiovisual_enhanced_shot_list"
    ].startswith("audiovisual_enhanced_shot_list_v")
    assert final_package["art_package"]["style_profile"]
    assert final_package["art_package"]["character_assets"]
    assert final_package["art_package"]["scene_assets"]
    assert final_package["audiovisual_enhanced_shot_list"]
    final_shot = final_package["audiovisual_enhanced_shot_list"][0]
    assert final_shot["scene"]
    assert isinstance(final_shot["characters"], list)
    assert isinstance(final_shot["props"], list)

    stored_final_package = ArtifactStore().load(
        artifact_refs["final_package"],
        job_id="job_full_v4_001",
    )
    assert stored_final_package.content["art_package"] == final_package["art_package"]
    assert (
        stored_final_package.content["audiovisual_enhanced_shot_list"]
        == final_package["audiovisual_enhanced_shot_list"]
    )

    for key in (
        "writer_package",
        "script_review",
        "quality_score",
        "director_package",
        "audiovisual_package",
        "art_package",
        "asset_registry",
        "final_package",
    ):
        assert key in artifact_refs
