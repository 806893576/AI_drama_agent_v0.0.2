from agents.brief_agent import analyze_brief
from domain.brief.validators import validate_brief
from graph.edges import route_after_brief_gate
from graph.nodes.agent_node import brief_agent_node
from schemas.enums import NodeId
from services.storage.artifact_store import ArtifactStore


def test_brief_agent_extracts_core_fields() -> None:
    result = analyze_brief(
        "我要做一个都市逆袭短剧，平台抖音，12集，每集2分钟，强爽点，讲女主夺回公司。"
    )

    brief = result.creative_brief

    assert brief.genre == "都市逆袭"
    assert brief.platform == "抖音"
    assert brief.episode_count == 12
    assert brief.episode_duration_minutes == 2
    assert brief.story_seed is not None
    assert result.validation.is_complete is True


def test_brief_agent_extracts_explicit_genre_field() -> None:
    result = analyze_brief(
        "美术风格：邵氏电影风格、复古港风。题材：古装武侠题材。"
        "平台：抖音。集数：1集。单集时长：2分钟。故事种子：武林大会决斗。"
    )

    assert result.creative_brief.genre == "古装武侠"
    assert result.validation.is_complete is True


def test_validate_brief_reports_missing_fields() -> None:
    result = analyze_brief("我要做一个强爽点短剧。")
    validation = validate_brief(result.creative_brief)

    assert validation.is_complete is False
    assert "genre" in validation.missing_fields
    assert "platform" in validation.missing_fields
    assert validation.questions_for_user


def test_brief_agent_node_returns_partial_state_update() -> None:
    job_id = "job_brief_agent_unit"
    update = brief_agent_node(
        {
            "job_id": job_id,
            "user_request": "都市逆袭短剧，平台抖音，12集，每集2分钟，强爽点。",
        }
    )

    assert update["current_stage"]
    assert update["artifact_refs"]["creative_brief"].artifact_id == "creative_brief_v001"
    assert update["artifact_refs"]["brief_validation"].artifact_id == "brief_validation_v001"
    assert update["creative_brief"].genre == "都市逆袭"
    assert update["brief_validation"].is_complete is True
    assert update["events"]

    store = ArtifactStore()
    assert store.exists(update["artifact_refs"]["creative_brief"], job_id=job_id)
    assert store.exists(update["artifact_refs"]["brief_validation"], job_id=job_id)


def test_route_after_brief_gate() -> None:
    complete = analyze_brief(
        "都市逆袭短剧，平台抖音，12集，每集2分钟，讲女主夺回公司。"
    )
    incomplete = analyze_brief("强爽点短剧。")

    assert (
        route_after_brief_gate({"brief_validation": complete.validation})
        == NodeId.PRODUCER_ROUTER.value
    )
    assert (
        route_after_brief_gate({"brief_validation": incomplete.validation})
        == NodeId.HUMAN_CONFIRM.value
    )
