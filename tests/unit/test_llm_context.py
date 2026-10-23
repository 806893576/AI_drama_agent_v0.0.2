from domain.story.character_bible import CharacterBible, CharacterProfile, CharacterRelationship
from domain.story.story_bible import StoryBible
from domain.story.story_synopsis import CharacterArcSummary, StorySynopsis, TurningPoint
from services.llm.context import (
    render_character_bible_context,
    render_creative_context,
)


def test_story_artifacts_render_to_natural_language_context() -> None:
    story_bible = StoryBible(
        story_bible_id="story_bible_v001",
        title="夺权千金",
        summary="女主被副手夺走公司后，利用账本和董事会规则夺回主动权。",
        theme="主动权来自信息与行动。",
        world_rules=["每集必须有明确反击爽点。"],
        core_conflict="女主必须在三天内阻止反派转移资产。",
        timeline_rules=["三集三天。"],
        immutable_facts=["女主最终夺回原公司。"],
    )
    story_synopsis = StorySynopsis(
        story_synopsis_id="story_synopsis_v001",
        premise="女主在董事会上被罢免，但带走关键账本。",
        protagonist_goal="夺回公司控制权。",
        main_story_arc="从被罢免，到争取盟友，再到股东大会反杀。",
        major_turning_points=[
            TurningPoint(
                turning_point_id="TP_01",
                title="带走账本",
                description="女主离场前拿走证据。",
                story_effect="保留翻盘底牌。",
            )
        ],
        major_conflicts=["董事会夺权"],
        causal_chain=["因为女主掌握账本，所以她能迫使财务总监反水。"],
        character_arcs=[
            CharacterArcSummary(character_role="protagonist", arc="从被动失势到主动掌局。")
        ],
        climax="股东大会公开证据。",
        resolution="女主恢复 CEO 职位。",
    )

    context = render_creative_context(story_bible, story_synopsis, title="测试上下文")

    assert "【测试上下文】" in context
    assert "故事标题：夺权千金" in context
    assert "关键转折" in context
    assert "因为女主掌握账本" in context


def test_character_bible_context_uses_simplified_relationship_cards() -> None:
    bible = CharacterBible(
        character_bible_id="character_bible_v001",
        characters=[
            CharacterProfile(
                character_id="CHAR_001",
                name="林晚",
                role="protagonist",
                identity="盛世公司原 CEO",
                personality=["冷静", "果断"],
                motivation="夺回公司并证明自己。",
                external_goal="夺回 CEO 职位。",
                internal_goal="重新掌控人生主动权。",
                voice_style="短句锋利。",
                visual_keywords=["职业套装", "克制"],
                story_function="承载主线爽点。",
                character_arc="从被夺权到主动掌局。",
            )
        ],
        relationships=[
            CharacterRelationship(
                relationship_id="REL_001",
                source_character_id="CHAR_001",
                target_character_id="CHAR_002",
                type="enemy",
                reason=["被副手背叛"],
                current_state="公开对抗",
            )
        ],
    )

    serialized = bible.model_dump(mode="json")
    context = render_character_bible_context(bible)

    assert "relationship_arcs" not in serialized
    assert "episode_presence" not in serialized["characters"][0]
    assert serialized["relationships"][0]["description"] == "被副手背叛"
    assert "公开对抗" in serialized["relationships"][0]["change_arc"]
    assert "林晚" in context
    assert "关系：enemy" in context
