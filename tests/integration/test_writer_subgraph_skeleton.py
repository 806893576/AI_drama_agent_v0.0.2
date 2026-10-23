from domain.brief.schemas import CreativeBrief
from graph.subgraphs.writer.graph import build_writer_subgraph
from schemas.enums import ArtifactType


def test_writer_subgraph_skeleton_runs_all_steps() -> None:
    graph = build_writer_subgraph()

    result = graph.invoke(
        {
            "job_id": "job_writer_001",
            "user_request": "都市逆袭短剧，平台抖音，12集，每集2分钟。",
            "creative_brief": CreativeBrief(
                genre="都市逆袭",
                platform="抖音",
                episode_count=12,
                episode_duration_minutes=2,
                tone="强爽点",
                story_seed="女主被夺走公司后重新夺回主动权。",
            ),
            "artifact_refs": {},
            "events": [],
        }
    )

    artifact_refs = result["artifact_refs"]

    assert "story_bible" in artifact_refs
    assert "story_synopsis" in artifact_refs
    assert "character_bible" in artifact_refs
    assert "episode_outline" in artifact_refs
    assert "episode_script" in artifact_refs
    assert "dialogue_polish" in artifact_refs
    assert "writer_package" in artifact_refs

    assert result["writer_subgraph_completed"] is True
    assert artifact_refs["story_bible"].artifact_type == ArtifactType.STORY_BIBLE
    assert artifact_refs["story_synopsis"].artifact_type == ArtifactType.STORY_SYNOPSIS
    assert artifact_refs["writer_package"].artifact_id.startswith("writer_package_v")
    assert result["story_synopsis"].causal_chain
    assert result["episode_scripts"]


def test_writer_subgraph_pauses_after_episode_outline_when_enabled() -> None:
    graph = build_writer_subgraph()

    result = graph.invoke(
        {
            "job_id": "job_writer_outline_confirm_001",
            "user_request": "都市逆袭短剧，平台抖音，3集，每集2分钟。",
            "creative_brief": CreativeBrief(
                genre="都市逆袭",
                platform="抖音",
                episode_count=3,
                episode_duration_minutes=2,
                tone="强爽点",
                story_seed="女主被夺走公司后重新夺回主动权。",
            ),
            "execution_options": {"enable_human_confirmations": True},
            "confirmed_human_points": ["brief", "style"],
            "artifact_refs": {},
            "events": [],
        }
    )

    artifact_refs = result["artifact_refs"]

    assert result["human_confirmation_required"] is True
    assert result["human_confirmation_point"] == "episode_outline"
    assert "episode_outline" in artifact_refs
    assert "episode_outline" in result["editable_artifact_refs"]
    assert "episode_script" not in artifact_refs
