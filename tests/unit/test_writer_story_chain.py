from domain.brief.schemas import CreativeBrief
from domain.story.story_bible import StoryBible
from domain.story.story_synopsis import CharacterArcSummary, StorySynopsis, TurningPoint
from graph.subgraphs.writer.nodes import (
    build_character_bible,
    build_episode_outline_package,
    build_episode_scripts,
    build_story_bible,
    build_story_synopsis,
)


def test_writer_story_chain_generates_synopsis_then_characters_then_outline() -> None:
    brief = CreativeBrief(
        genre="都市逆袭",
        platform="抖音",
        episode_count=12,
        episode_duration_minutes=2,
        tone="强爽点、快节奏",
        story_seed="女主被夺走公司后重新夺回主动权。",
    )

    story_bible = build_story_bible(brief)
    story_synopsis = build_story_synopsis(brief, story_bible)
    character_bible = build_character_bible(story_bible, story_synopsis)
    outline_package = build_episode_outline_package(
        brief,
        story_bible,
        story_synopsis,
        character_bible,
    )

    assert story_bible.summary
    assert story_synopsis.causal_chain
    assert story_synopsis.parent_artifact_id == story_bible.story_bible_id
    assert character_bible.parent_artifact_id == story_synopsis.story_synopsis_id
    assert character_bible.characters[0].role == "protagonist"
    assert outline_package.parent_artifact_ids == [
        "story_bible_v001",
        "story_synopsis_v001",
        "character_bible_v001",
    ]
    assert len(outline_package.episodes) == 12
    assert outline_package.episodes[0].opening_hook
    assert outline_package.episodes[0].episode_positioning

    episode_scripts = build_episode_scripts(brief, story_bible, outline_package, character_bible)
    first_script = episode_scripts[0].model_dump(mode="json")
    first_scene = first_script["scenes"][0]

    assert first_script["project_metadata"]["title"] == story_bible.title
    assert first_script["episode"]["episode_number"] == 1
    assert first_script["episode"]["appearing_characters"]
    assert "script_text" in first_scene
    assert "lighting" not in first_scene
    assert "atmosphere" not in first_scene
    assert "dialogue" not in first_scene


def test_writer_fallback_uses_story_specific_fantasy_entities_and_events() -> None:
    story_bible = StoryBible(
        story_bible_id="story_bible_v001",
        title="异世界卡车：魔王后宫炸裂开局",
        summary="男主被卡车撞飞后穿越异世界，靠受致命伤触发爆炸的卡车之力，击败魔王军并收服精灵公主、龙族少女和魔王。",
        theme="废柴用反套路方式逆袭。",
        world_rules=["剑与魔法异世界", "卡车爆炸被动无法主动开启", "魔王和后宫角色存在好感度崩坏"],
        core_conflict="男主必须在3集内从废物勇者成长为击败魔王的反套路强者。",
        timeline_rules=["第1集穿越并触发爆炸", "第2集反杀龙族少女", "第3集击败魔王并收束"],
        immutable_facts=["男主被卡车撞死后穿越", "后宫成员包括精灵公主、龙族少女、魔王"],
    )
    story_synopsis = StorySynopsis(
        story_synopsis_id="story_synopsis_v001",
        parent_artifact_id="story_bible_v001",
        premise="男主被卡车撞飞后穿越异世界，开局被杂鱼魔将嘲笑为废物勇者。",
        protagonist_goal="外部目标：击败魔王军并活下去。内部目标：证明最惨开局也能变成逆袭起点。",
        main_story_arc="男主先因受伤触发爆炸秒杀魔将，再用连环爆炸反杀龙族少女，最终抱住魔王引爆完成终局逆袭。",
        major_turning_points=[
            TurningPoint(
                turning_point_id="TP_01",
                title="卡车穿越与初次爆炸",
                description="男主被魔将刺伤后触发毁灭冲击，炸飞敌人并接住精灵公主。",
                story_effect="建立卡车爆炸金手指和精灵公主关系线。",
            ),
            TurningPoint(
                turning_point_id="TP_02",
                title="龙族少女来袭",
                description="龙族少女压制男主，男主利用冷却间隔连续受伤引爆完成反杀。",
                story_effect="证明男主能把被动能力变成战术。",
            ),
            TurningPoint(
                turning_point_id="TP_03",
                title="魔王最终摊牌",
                description="魔王魔力屏障压制爆炸，男主主动抱住魔王引爆完成反转。",
                story_effect="魔王被击败并触发好感度崩坏。",
            ),
        ],
        major_conflicts=["男主爆炸被动无法主动开启", "魔王军层层压制男主", "魔王屏障免疫常规爆炸"],
        causal_chain=[
            "因为男主被卡车撞飞，所以他穿越并继承受伤触发爆炸的能力。",
            "因为魔将刺伤男主，所以毁灭冲击首次触发并炸飞敌人。",
            "因为龙族少女压制男主，所以男主利用冷却间隔制造连环爆炸。",
            "因为魔王免疫常规爆炸，所以男主主动抱住魔王引爆完成终局反转。",
        ],
        character_arcs=[
            CharacterArcSummary(
                character_role="protagonist",
                arc="从被嘲笑的废物勇者成长为主动撞向魔王的反套路强者。",
            )
        ],
        climax="男主抱住魔王引爆，爆炸撕裂空间并触发魔王好感度崩坏。",
        resolution="精灵公主、龙族少女和魔王围着男主争宠，男主用现代吐槽收尾。",
    )
    brief = CreativeBrief(
        genre="二次元穿越",
        platform="抖音",
        episode_count=3,
        episode_duration_minutes=2,
    )

    character_bible = build_character_bible(story_bible, story_synopsis)
    outline_package = build_episode_outline_package(
        brief,
        story_bible,
        story_synopsis,
        character_bible,
    )

    names = [character.name for character in character_bible.characters]
    assert names == ["男主", "魔王", "精灵公主", "龙族少女"]
    assert "林夏" not in names
    assert "周启明" not in names
    first_events = outline_package.episodes[0].key_events
    assert "主角发现一个可执行线索。" not in first_events
    assert any("卡车" in event or "爆炸" in event or "精灵公主" in event for event in first_events)
    assert "魔王" in outline_package.episodes[-1].turning_point_and_climax


def test_story_synopsis_fallback_keeps_toilet_reincarnation_setting() -> None:
    story_bible = StoryBible(
        story_bible_id="story_bible_v001",
        title="转生成马桶：我在女厕当吐槽役",
        summary=(
            "男主在现实世界被卡车撞飞后，穿越到剑与魔法与奇怪科技共存的异世界，"
            "成为冒险者公会旁公共女厕里的一个智能马桶。他保留完整的人类意识和吐槽能力，"
            "却无法说话、无法移动，只能通过冲水、喷水、加热、烘干、开关盖板等方式互动。"
            "三集内完成从绝望吐槽到认真思考马桶也能帮助他人的转变，并在结尾留下恢复人形的隐藏线索。"
        ),
        theme="尊严不取决于形态，而在于你如何对待眼前的每一个人。",
        world_rules=[
            "主角被绑定为公共女厕所第三隔间的白色智能马桶。",
            "主角只能控制温水冲洗、座圈加热、暖风烘干、冲水、盖板开合五项功能。",
            "隐私保护机制会强制启动，笑点必须来自身份错位和沟通误会。",
        ],
        core_conflict="主角拥有人类灵魂，却被困在无法言语、无法移动的马桶中，渴望证明身份并解除诅咒。",
        timeline_rules=[
            "每集围绕一次厕所来访事件完整收束。",
            "三集之内，没有任何角色真正确认这个马桶是穿越者。",
        ],
        immutable_facts=[
            "主角前世是被卡车撞飞后死亡的普通年轻男性。",
            "主角唯一的互动途径是马桶的五项基础功能。",
            "系统只允许在结尾展示模糊恢复人形线索。",
        ],
    )
    brief = CreativeBrief(
        genre="二次元穿越喜剧",
        platform="抖音",
        episode_count=3,
        episode_duration_minutes=2,
    )

    story_synopsis = build_story_synopsis(brief, story_bible)

    serialized = story_synopsis.model_dump_json()
    assert "马桶" in story_synopsis.premise
    assert "恢复人形" in story_synopsis.resolution
    assert any("冲水" in step or "盖板" in step for step in story_synopsis.causal_chain)
    assert any("隐私" in conflict for conflict in story_synopsis.major_conflicts)
    assert "夺回被夺走的主动权" not in serialized
    assert "最终摊牌" not in serialized
    assert "证据" not in serialized


def test_episode_script_fallback_preserves_story_seed_anchors() -> None:
    brief = CreativeBrief(
        genre="青春悬疑",
        platform="抖音",
        episode_count=1,
        episode_duration_minutes=2,
        tone="清冷、悬念",
        story_seed="高中生许宁在雨后车站发现旧游戏机里多出一段失踪同学留下的像素录像，她必须在末班车前确认录像地点。",
    )

    story_bible = build_story_bible(brief)
    story_synopsis = build_story_synopsis(brief, story_bible)
    character_bible = build_character_bible(story_bible, story_synopsis)
    outline_package = build_episode_outline_package(
        brief,
        story_bible,
        story_synopsis,
        character_bible,
    )

    episode_scripts = build_episode_scripts(
        brief,
        story_bible,
        outline_package,
        character_bible,
    )
    script_text = "\n".join(
        scene.script_text
        for script in episode_scripts
        for scene in script.scenes
    )

    for anchor in ("许宁", "车站", "旧游戏机", "失踪同学", "像素录像"):
        assert anchor in script_text
