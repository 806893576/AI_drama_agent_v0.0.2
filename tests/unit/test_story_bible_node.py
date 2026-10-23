from domain.brief.schemas import CreativeBrief
from graph.subgraphs.writer.nodes import build_story_bible, create_story_bible_node
from schemas.enums import ArtifactType


def test_build_story_bible_from_creative_brief() -> None:
    brief = CreativeBrief(
        genre="都市逆袭",
        platform="抖音",
        episode_count=12,
        episode_duration_minutes=2,
        tone="强爽点",
        story_seed="女主被夺走公司后重新夺回主动权。",
    )

    story_bible = build_story_bible(brief)

    assert story_bible.story_bible_id == "story_bible_v001"
    assert "都市逆袭" in story_bible.title
    assert "抖音" in story_bible.summary
    assert story_bible.world_rules
    assert story_bible.immutable_facts


def test_create_story_bible_node_saves_artifact(tmp_path, monkeypatch) -> None:
    # 如果你的 ArtifactStore 默认写 storage/artifacts，
    # 这里可以通过 monkeypatch 修改当前目录，或接受写入本地 storage。
    # 更推荐后续把 ArtifactStore 注入节点；MVP 阶段先测试主要返回结构。
    brief = CreativeBrief(
        genre="都市逆袭",
        platform="抖音",
        episode_count=12,
        episode_duration_minutes=2,
        tone="强爽点",
        story_seed="女主夺回公司。",
    )

    update = create_story_bible_node(
        {
            "job_id": "job_story_bible_unit",
            "creative_brief": brief,
            "artifact_refs": {},
            "events": [],
        }
    )

    ref = update["artifact_refs"]["story_bible"]

    assert ref.artifact_type == ArtifactType.STORY_BIBLE
    assert update["story_bible"].core_conflict
    assert update["events"]
