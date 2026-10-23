from domain.brief.schemas import CreativeBrief
from domain.directing.scene_breakdown import SceneBreakdown
from domain.story.character_bible import CharacterBible, CharacterProfile
from domain.story.episode_script import (
    EpisodeCharacter,
    EpisodeLevel,
    EpisodeScript,
    ProjectMetadata,
    SceneScript,
)


def test_creative_brief_defaults() -> None:
    brief = CreativeBrief(genre="都市逆袭")
    assert brief.genre == "都市逆袭"
    assert brief.style_keywords == []
    assert brief.constraints == []


def test_character_bible_contains_stable_character_id() -> None:
    profile = CharacterProfile(
        character_id="char_001",
        name="林夏",
        role="protagonist",
        external_goal="夺回属于自己的公司",
        motivation="证明自己并保护家人",
        voice_style="克制、锋利、短句多",
    )
    bible = CharacterBible(character_bible_id="character_bible_v001", characters=[profile])
    assert bible.characters[0].character_id == "char_001"
    assert bible.characters[0].role_type == "protagonist"


def test_episode_script_uses_compact_scene_text_structure() -> None:
    scene = SceneScript(
        scene_number=1,
        interior_exterior="内景",
        location="会议室",
        time="日",
        continuity="紧接上一场",
        script_text="林夏站在会议室门口，压住情绪。\n林夏：这一次，我不会再退。",
    )
    script = EpisodeScript(
        episode_script_id="episode_script_ep001_v001",
        project_metadata=ProjectMetadata(
            title="她的名字被删掉了",
            genre="都市逆袭",
            total_episodes=12,
        ),
        episode=EpisodeLevel(
            episode_number=1,
            episode_title="会议室里的陌生人",
            core_function="女主失去公司署名权，结尾抛出她握有核心证据。",
            appearing_characters=[EpisodeCharacter(name="林夏", brief="女主，前技术负责人。")],
            ending_hook="屏幕弹出新的证据文件。",
        ),
        scenes=[scene],
    )
    dumped = script.model_dump(mode="json")

    assert dumped["episode"]["episode_number"] == 1
    assert dumped["scenes"][0]["time"] == "日"
    assert dumped["scenes"][0]["continuity"] == "紧接上一场"
    assert "lighting" not in dumped["scenes"][0]
    assert "atmosphere" not in dumped["scenes"][0]
    assert "dialogue" not in dumped["scenes"][0]


def test_scene_breakdown_coerces_nested_values_to_text() -> None:
    breakdown = SceneBreakdown(
        scene_id="EP_001_SC_001",
        episode_id="EP_001",
        scene_number=1,
        interior_exterior="内景",
        time="日",
        location="会议室",
        characters={"主角": "林夏", "配角": ["周延", "前台"]},
        props=["手机", "合同"],
        costume_makeup="林夏：职业套装；周延：商务西装",
        scene_summary="林夏进入会议室，被告知董事会已经开始。",
        key_actions=["林夏推门进入", "周延按下遥控器"],
        dramatic_function="让主角发现自己被排除在权力核心之外。",
        continuity=["林夏手里仍拿着手机", "合同位置后续镜头保持一致。"],
    )

    assert breakdown.characters == "主角：林夏；配角：周延；前台"
    assert breakdown.props == "手机；合同"
    assert breakdown.costume_makeup == "林夏：职业套装；周延：商务西装"
    assert breakdown.key_actions == "林夏推门进入；周延按下遥控器"
    assert breakdown.continuity == "林夏手里仍拿着手机；合同位置后续镜头保持一致。"
