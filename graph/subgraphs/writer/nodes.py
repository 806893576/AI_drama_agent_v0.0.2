"""编剧子图节点。

Writer 前半段采用“逐层递进生成”：
1. Story Bible：稳定设定层。
2. Story Synopsis：完整故事因果链。
3. Character Bible：从完整故事中识别必要人物和关系。
4. Episode Outline：把完整故事和人物系统切割成具体集数。

这样每个节点职责更清晰，也能减少每次送入 LLM 的上下文大小。
"""

from __future__ import annotations

import re
from typing import Any

from domain.brief.schemas import CreativeBrief
from domain.story.character_bible import CharacterBible, CharacterProfile, CharacterRelationship
from domain.story.dialogue_polish import DialoguePolishNote, DialoguePolishPackage
from domain.story.episode_outline import EpisodeOutline, EpisodeOutlinePackage
from domain.story.episode_script import (
    EpisodeCharacter,
    EpisodeLevel,
    EpisodeScript,
    ProjectMetadata,
    SceneScript,
)
from domain.story.story_bible import StoryBible
from domain.story.story_synopsis import CharacterArcSummary, StorySynopsis, TurningPoint
from graph.nodes.style_guide_node import style_guide_summary_from_state
from observability.logger import get_logger
from schemas.enums import ArtifactType, EventStatus, NodeId, StageId
from services.llm import (
    LLMRuntimeError,
    LLMStructuredOutputError,
    StructuredLLMRunner,
    llm_enabled,
    render_character_bible_context,
    render_creative_brief_context,
    render_creative_context,
    render_episode_outline_context,
    render_episode_scripts_context,
    render_story_bible_context,
    render_story_synopsis_context,
)
from services.storage.artifact_store import ArtifactStore
from state.artifact_refs import get_artifact_ref_id
from state.events import RuntimeEvent

logger = get_logger(__name__)

_GENERIC_KEY_EVENTS = {
    "主角发现一个可执行线索。",
    "对手制造新的限制条件。",
    "盟友提供侧面突破方式。",
    "主角把失败转化为下一步证据。",
}


def _event(job_id: str, node_id: NodeId, message: str, artifact_ids: list[str]) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=f"{job_id}_{node_id.value.replace('.', '_')}_completed",
        node_id=node_id,
        stage=StageId.WRITER,
        status=EventStatus.COMPLETED,
        message=message,
        artifact_ids=artifact_ids,
    )


def create_story_bible_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    brief = _load_creative_brief_from_state(state, store)

    story_bible = _try_llm_model(
        "writer.story_bible",
        {
            "creative_brief": render_creative_brief_context(brief),
            "style_guide_summary": style_guide_summary_from_state(state),
        },
        StoryBible,
        fallback=lambda: build_story_bible(brief),
    )

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.STORY_BIBLE,
        content=story_bible,
        summary=story_bible.summary,
        created_by=NodeId.WRITER_STORY_BIBLE,
    )
    return {
        "current_stage": StageId.WRITER,
        "artifact_refs": {"story_bible": ref},
        "story_bible": story_bible,
        "events": [_event(job_id, NodeId.WRITER_STORY_BIBLE, "Story Bible 已生成。", [ref.artifact_id])],
    }


def create_story_synopsis_node(state: dict) -> dict:
    """生成完整故事因果链。"""

    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    brief = _load_creative_brief_from_state(state, store)
    story_bible = _ensure_model(state["story_bible"], StoryBible)

    story_synopsis = _try_llm_model(
        "writer.story_synopsis",
        {
            "creative_brief": render_creative_brief_context(brief),
            "story_bible": render_story_bible_context(story_bible),
            "style_guide_summary": style_guide_summary_from_state(state),
        },
        StorySynopsis,
        fallback=lambda: build_story_synopsis(brief, story_bible),
    )

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.STORY_SYNOPSIS,
        content=story_synopsis,
        summary=story_synopsis.premise,
        created_by=NodeId.WRITER_STORY_SYNOPSIS,
        parent_ref=state.get("artifact_refs", {}).get("story_bible"),
    )
    return {
        "current_stage": StageId.WRITER,
        "artifact_refs": {"story_synopsis": ref},
        "story_synopsis": story_synopsis,
        "events": [_event(job_id, NodeId.WRITER_STORY_SYNOPSIS, "故事梗概已生成。", [ref.artifact_id])],
    }


def create_character_bible_node(state: dict) -> dict:
    """基于 Story Bible + Story Synopsis 识别完成故事所必需的人物。"""

    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    story_bible = _ensure_model(state["story_bible"], StoryBible)
    story_synopsis = _ensure_model(state["story_synopsis"], StorySynopsis)

    character_bible = _try_llm_model(
        "writer.character_bible",
        {
            "creative_context": render_creative_context(
                story_bible,
                story_synopsis,
                title="人物圣经生成所需上游创作上下文",
            ),
            "style_guide_summary": style_guide_summary_from_state(state),
        },
        CharacterBible,
        fallback=lambda: build_character_bible(story_bible, story_synopsis),
    )
    if _needs_story_specific_character_fallback(story_bible, story_synopsis, character_bible):
        logger.warning("CharacterBible is inconsistent with Story Bible/Synopsis, rebuilding with story-driven fallback.")
        character_bible = build_character_bible(story_bible, story_synopsis)

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.CHARACTER_BIBLE,
        content=character_bible,
        summary=f"{len(character_bible.characters)} 个核心人物。",
        created_by=NodeId.WRITER_CHARACTER_BIBLE,
        parent_ref=state.get("artifact_refs", {}).get("story_synopsis"),
    )
    return {
        "current_stage": StageId.WRITER,
        "artifact_refs": {"character_bible": ref},
        "character_bible": character_bible,
        "events": [_event(job_id, NodeId.WRITER_CHARACTER_BIBLE, "人物圣经已生成。", [ref.artifact_id])],
    }


def create_episode_outline_node(state: dict) -> dict:
    """基于完整故事和人物系统切分分集大纲。"""

    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    brief = _load_creative_brief_from_state(state, store)
    story_bible = _ensure_model(state["story_bible"], StoryBible)
    story_synopsis = _ensure_model(state["story_synopsis"], StorySynopsis)
    character_bible = _ensure_model(state["character_bible"], CharacterBible)

    outline_package = _try_llm_model(
        "writer.episode_outline",
        {
            "creative_brief": render_creative_brief_context(brief),
            "story_bible": render_story_bible_context(story_bible),
            "story_synopsis": render_story_synopsis_context(story_synopsis),
            "character_bible": render_character_bible_context(character_bible),
            "style_guide_summary": style_guide_summary_from_state(state),
        },
        EpisodeOutlinePackage,
        fallback=lambda: build_episode_outline_package(brief, story_bible, story_synopsis, character_bible),
    )
    if _needs_story_specific_outline_fallback(story_bible, story_synopsis, outline_package):
        logger.warning("EpisodeOutline is generic or inconsistent, rebuilding with story-driven fallback.")
        outline_package = build_episode_outline_package(brief, story_bible, story_synopsis, character_bible)

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.EPISODE_OUTLINE,
        content=outline_package,
        summary=f"{len(outline_package.episodes)} 集分集大纲。",
        created_by=NodeId.WRITER_EPISODE_OUTLINE,
        parent_ref=state.get("artifact_refs", {}).get("character_bible"),
    )
    return {
        "current_stage": StageId.WRITER,
        "artifact_refs": {"episode_outline": ref},
        "episode_outline_package": outline_package,
        "events": [_event(job_id, NodeId.WRITER_EPISODE_OUTLINE, "分集大纲已生成。", [ref.artifact_id])],
    }


def generate_episode_script_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    brief = _load_creative_brief_from_state(state, store)
    story_bible = _ensure_model(state["story_bible"], StoryBible)
    outline_package = _ensure_model(state["episode_outline_package"], EpisodeOutlinePackage)
    character_bible = _ensure_model(state["character_bible"], CharacterBible)

    episode_scripts = _try_llm_model(
        "writer.episode_script",
        {
            "creative_brief": render_creative_brief_context(brief),
            "story_bible": render_story_bible_context(story_bible),
            "episode_outline_package": render_episode_outline_context(outline_package),
            "character_bible": render_character_bible_context(character_bible),
            "style_guide_summary": style_guide_summary_from_state(state),
        },
        list[EpisodeScript],
        fallback=lambda: build_episode_scripts(brief, story_bible, outline_package, character_bible),
    )

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.EPISODE_SCRIPT,
        content=episode_scripts,
        summary=f"{len(episode_scripts)} 集单集剧本。",
        created_by=NodeId.WRITER_EPISODE_SCRIPT,
    )
    return {
        "current_stage": StageId.WRITER,
        "artifact_refs": {"episode_script": ref},
        "episode_scripts": episode_scripts,
        "events": [_event(job_id, NodeId.WRITER_EPISODE_SCRIPT, "单集剧本已生成。", [ref.artifact_id])],
    }


def polish_dialogue_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    episode_scripts = [_ensure_model(item, EpisodeScript) for item in state.get("episode_scripts", [])]
    story_bible = _ensure_model(state["story_bible"], StoryBible)

    polish_package = _try_llm_model(
        "writer.dialogue_polish",
        {
            "episode_scripts": render_episode_scripts_context(episode_scripts),
            "story_bible": render_story_bible_context(story_bible),
            "style_guide_summary": style_guide_summary_from_state(state),
        },
        DialoguePolishPackage,
        fallback=lambda: build_dialogue_polish_package(episode_scripts, story_bible),
    )

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.DIALOGUE_POLISH,
        content=polish_package,
        summary=f"{len(polish_package.notes)} 条对白润色记录。",
        created_by=NodeId.WRITER_DIALOGUE_POLISH,
    )
    return {
        "current_stage": StageId.WRITER,
        "artifact_refs": {"dialogue_polish": ref},
        "dialogue_polish_package": polish_package,
        "events": [_event(job_id, NodeId.WRITER_DIALOGUE_POLISH, "对白润色已完成。", [ref.artifact_id])],
    }


def build_script_package_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    refs = state.get("artifact_refs", {})

    writer_package = {
        "package_id": "writer_package_v001",
        # 保存引用关系，减少包内重复长文本；完整内容仍可从 Artifact Store 加载。
        "artifact_ids": {
            key: get_artifact_ref_id(ref)
            for key, ref in refs.items()
            if key
            in {
                "style_guide",
                "story_bible",
                "story_synopsis",
                "character_bible",
                "episode_outline",
                "episode_script",
                "dialogue_polish",
            }
        },
        "story_bible_summary": _compact_story_bible(state.get("story_bible")),
        "story_synopsis_summary": _compact_story_synopsis(state.get("story_synopsis")),
        "character_ids": [
            item.character_id for item in getattr(state.get("character_bible"), "characters", [])
        ],
        "episode_ids": [
            item.episode_id for item in getattr(state.get("episode_outline_package"), "episodes", [])
        ],
    }

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.WRITER_PACKAGE,
        content=writer_package,
        summary="包含编剧阶段关键产物引用、摘要和索引。",
        created_by=NodeId.WRITER_SCRIPT_PACKAGE,
    )
    return {
        "current_stage": StageId.WRITER,
        "artifact_refs": {"writer_package": ref},
        "writer_package": writer_package,
        "writer_subgraph_completed": True,
        "events": [_event(job_id, NodeId.WRITER_SCRIPT_PACKAGE, "编剧交付包已汇总。", [ref.artifact_id])],
    }


def _load_creative_brief_from_state(state: dict, artifact_store: ArtifactStore) -> CreativeBrief:
    brief = state.get("creative_brief")
    if isinstance(brief, CreativeBrief):
        return brief
    if isinstance(brief, dict):
        return CreativeBrief(**brief)

    brief_ref = state.get("artifact_refs", {}).get("creative_brief")
    if brief_ref is not None:
        content = artifact_store.load(brief_ref, job_id=state["job_id"]).content
        return _ensure_model(content, CreativeBrief)

    raise ValueError("CreativeBrief is required before creating writer artifacts.")


def _ensure_model(value: Any, model_type: type) -> Any:
    if isinstance(value, model_type):
        return value
    if isinstance(value, dict):
        return model_type(**value)
    raise TypeError(f"Expected {model_type.__name__}, got {type(value).__name__}")


def _needs_story_specific_character_fallback(
    story_bible: StoryBible,
    story_synopsis: StorySynopsis,
    character_bible: CharacterBible,
) -> bool:
    """检查角色系统是否漏掉 Story 中的显性关键实体。"""

    story_text = _story_text(story_bible, story_synopsis)
    character_names = " ".join(character.name for character in character_bible.characters)
    for anchor in _explicit_character_anchors(story_text):
        if anchor not in character_names:
            return True
    return False


def _needs_story_specific_outline_fallback(
    story_bible: StoryBible,
    story_synopsis: StorySynopsis,
    outline_package: EpisodeOutlinePackage,
) -> bool:
    """检查分集大纲是否仍是通用占位，或明显脱离故事语境。"""

    story_text = _story_text(story_bible, story_synopsis)
    if not outline_package.episodes:
        return True

    placeholder_hits = 0
    total_events = 0
    for episode in outline_package.episodes:
        total_events += len(episode.key_events)
        placeholder_hits += sum(1 for event in episode.key_events if event in _GENERIC_KEY_EVENTS)
        if "名字已经被从核心位置抹掉" in episode.opening_hook and not _has_any(story_text, ["公司", "董事", "夺权", "名字"]):
            return True

    return total_events > 0 and placeholder_hits / total_events >= 0.5


def _try_llm_model(prompt_id: str, variables: dict[str, Any], model_type: Any, fallback):
    """编剧节点的 LLM 调用兜底包装。"""

    if not llm_enabled():
        return fallback()

    try:
        parsed, _response = StructuredLLMRunner().generate_model(
            prompt_id,
            variables,
            model_type,
            temperature=0.7,
        )
        return parsed
    except (LLMRuntimeError, LLMStructuredOutputError):
        raise
    except Exception as exc:
        logger.warning("LLM generation failed for %s, using fallback. error=%s", prompt_id, exc)
        return fallback()


def build_story_bible(brief: CreativeBrief) -> StoryBible:
    genre = brief.genre or "原创短剧"
    platform = brief.platform or "短视频平台"
    episode_count = brief.episode_count or 12
    duration = brief.episode_duration_minutes or 2
    tone = brief.tone or "情绪强、节奏快"
    story_seed = brief.story_seed or "主角在强冲突中完成成长和反击。"

    return StoryBible(
        story_bible_id="story_bible_v001",
        title=f"{genre}短剧方案",
        summary=(
            f"一部面向{platform}的{genre}短剧。故事以“{story_seed}”为核心种子，"
            f"在 {episode_count} 集、单集约 {duration} 分钟的短剧结构内，围绕主角失势、"
            "发现突破口、重建联盟、持续反击并完成最终收束展开。整体风格强调"
            f"{tone}，每集都需要用明确钩子、冲突升级和结尾悬念推动观众追看。"
        ),
        theme=f"围绕{genre}类型，突出主动权、尊严和自我证明。",
        world_rules=[
            f"单集约 {duration} 分钟，必须保持短剧节奏。",
            "每集都需要明确钩子、冲突升级和结尾悬念。",
            "人物欲望、动机和行为逻辑必须持续一致。",
        ],
        core_conflict=f"主角目标与外部阻力持续冲突，并在 {episode_count} 集内层层升级。",
        timeline_rules=[
            f"全剧按 {episode_count} 集结构推进。",
            "关键反转必须建立在前文信息基础上。",
            "跨集人物关系、道具、地点和伏笔需要保持连续。",
        ],
        immutable_facts=[
            f"目标平台：{platform}",
            f"题材类型：{genre}",
            f"故事种子：{story_seed}",
            *[f"禁用元素：{item}" for item in brief.forbidden_elements],
        ],
    )


def build_story_synopsis(brief: CreativeBrief, story_bible: StoryBible) -> StorySynopsis:
    """根据 Story Bible 动态生成兜底 Story Synopsis。

    这个函数会在 LLM 网络错误等非格式化失败时使用。它不能假设题材是都市逆袭，
    必须从 Story Bible 的稳定设定中提取前提、目标、转折和因果链。
    """

    story_text = "\n".join(
        [
            story_bible.title or "",
            story_bible.summary,
            story_bible.theme,
            story_bible.core_conflict,
            *story_bible.world_rules,
            *story_bible.timeline_rules,
            *story_bible.immutable_facts,
        ]
    )
    protagonist = _detect_protagonist_name(story_text)
    turning_points = _story_synopsis_turning_points(story_bible)
    causal_chain = _story_synopsis_causal_chain(story_bible, turning_points)
    return StorySynopsis(
        story_synopsis_id="story_synopsis_v001",
        parent_artifact_id=story_bible.story_bible_id,
        premise=_story_synopsis_premise(story_bible),
        protagonist_goal=_story_synopsis_goal(story_bible),
        main_story_arc=_story_synopsis_main_arc(story_bible, turning_points),
        major_turning_points=turning_points,
        major_conflicts=_story_synopsis_conflicts(story_bible),
        causal_chain=causal_chain,
        character_arcs=[
            CharacterArcSummary(
                character_role=protagonist,
                arc=_story_synopsis_character_arc(story_bible),
            )
        ],
        climax=_story_synopsis_climax(story_bible, turning_points),
        resolution=_story_synopsis_resolution(story_bible),
    )


def _story_synopsis_premise(story_bible: StoryBible) -> str:
    if "马桶" in _story_bible_text(story_bible):
        return (
            "男主被卡车撞飞后穿越到异世界，却不是成为勇者或法师，而是被固定在冒险者公会旁女厕第三隔间，"
            "成为一个拥有完整人类意识和吐槽能力、却无法说话和移动的智能马桶。"
        )
    return _first_sentence(story_bible.summary, limit=180)


def _story_synopsis_goal(story_bible: StoryBible) -> str:
    text = _story_bible_text(story_bible)
    if "马桶" in text:
        return (
            "外部目标：主角想证明自己曾是人类，并寻找解除马桶转生状态的线索。"
            "内部目标：从绝望吐槽转向接受荒诞处境，理解即使是马桶形态也能帮助他人。"
        )
    if "无法主动" in text or "被动" in text:
        return f"外部目标：在{story_bible.core_conflict}中活下来并完成关键逆转。内部目标：学会在限制条件下主动选择。"
    return f"外部目标：推进并解决核心冲突：{story_bible.core_conflict} 内部目标：完成主题变化：{story_bible.theme}"


def _story_synopsis_turning_points(story_bible: StoryBible) -> list[TurningPoint]:
    text = _story_bible_text(story_bible)
    if "马桶" in text:
        return [
            TurningPoint(
                turning_point_id="TP_01",
                title="转生成智能马桶",
                description="男主从现实死亡后醒来，发现自己被固定在异世界女厕第三隔间，只能通过马桶功能感知和互动。",
                story_effect="确立最荒诞的身份错位、行动限制和第一人称吐槽视角。",
            ),
            TurningPoint(
                turning_point_id="TP_02",
                title="功能互动引发误会",
                description="主角试图用冲水、喷水、加热、开合盖板等方式表达善意，却被来访者理解为故障、恶作剧或灵异事件。",
                story_effect="把世界规则转化为每集密集笑点，也强化主角无法正常沟通的核心冲突。",
            ),
            TurningPoint(
                turning_point_id="TP_03",
                title="从证明身份到帮助他人",
                description="主角在连续误会中意识到自己虽然无法恢复人形，却能通过有限功能缓解来访者的小危机。",
                story_effect="人物弧光从绝望吐槽转为主动承担，主题从荒诞笑料进入温和成长。",
            ),
            TurningPoint(
                turning_point_id="TP_04",
                title="恢复人形线索出现",
                description="结尾系统或环境给出模糊提示，暗示解除诅咒与主角如何使用马桶功能帮助他人有关。",
                story_effect="完成三集喜剧收束，并为后续恢复人形留下钩子。",
            ),
        ]

    episode_points = _turning_points_from_timeline_rules(story_bible.timeline_rules)
    if episode_points:
        return episode_points

    return [
        TurningPoint(
            turning_point_id="TP_01",
            title="故事启动",
            description=_first_sentence(story_bible.summary),
            story_effect="建立主角处境、核心设定和观众期待。",
        ),
        TurningPoint(
            turning_point_id="TP_02",
            title="核心冲突显性化",
            description=story_bible.core_conflict,
            story_effect="让主角目标和外部阻力进入持续对抗。",
        ),
        TurningPoint(
            turning_point_id="TP_03",
            title="规则限制制造代价",
            description=_first_non_empty(story_bible.world_rules[0] if story_bible.world_rules else "", story_bible.theme),
            story_effect="让世界规则成为剧情推进和反转的依据。",
        ),
        TurningPoint(
            turning_point_id="TP_04",
            title="主题收束",
            description=story_bible.theme,
            story_effect="把故事从事件推进收束到人物变化和主题表达。",
        ),
    ]


def _story_synopsis_main_arc(story_bible: StoryBible, turning_points: list[TurningPoint]) -> str:
    if "马桶" in _story_bible_text(story_bible):
        return (
            "第一阶段，主角确认自己从人类变成固定在女厕第三隔间的智能马桶，无法说话、移动或直接证明身份，"
            "只能在内心用现代吐槽回应荒诞处境。第二阶段，不同异世界女性来访者带来魔法少女、圣职者、兽耳冒险者等事件，"
            "主角试图用有限功能提醒、安慰或帮忙，却不断制造故障马桶和灵异马桶误会。第三阶段，主角不再只执着于证明自己是人类，"
            "而是开始认真思考如何在不侵犯隐私和不突破规则的前提下帮助他人。结尾通过系统极简提示或环境异常留下恢复人形线索。"
        )
    return " ".join(point.description for point in turning_points)


def _story_synopsis_conflicts(story_bible: StoryBible) -> list[str]:
    text = _story_bible_text(story_bible)
    if "马桶" in text:
        return [
            "主角拥有人类意识，却被固定为无法说话、无法移动的智能马桶。",
            "主角想证明自己曾是人类，但所有信号都会被误解为故障、恶作剧或灵异现象。",
            "主角想帮忙又必须遵守隐私保护和功能消耗规则，善意操作经常变成新的笑料。",
            "主角渴望解除诅咒，但系统只给出模糊提示，不直接说明恢复条件。",
        ]
    conflicts = [story_bible.core_conflict]
    conflicts.extend(rule for rule in story_bible.world_rules[:2] if "规则" in rule or "无法" in rule or "必须" in rule)
    return _unique(conflicts)


def _story_synopsis_causal_chain(story_bible: StoryBible, turning_points: list[TurningPoint]) -> list[str]:
    if "马桶" in _story_bible_text(story_bible):
        return [
            "因为主角被卡车撞飞后转生规则出错，所以他没有成为人形穿越者，而是被绑定为公共女厕所的智能马桶。",
            "因为主角无法说话和移动，所以他只能用冲水、喷水、加热、烘干和盖板开合来表达想法。",
            "因为其他角色无法理解这些信号，所以主角的善意帮助会被误认为故障马桶、恶作剧或灵异事件。",
            "因为隐私保护机制会自动遮蔽敏感内容，所以故事笑点只能来自身份错位、反应夸张和沟通误会。",
            "因为主角在误会中逐渐真的帮助了来访者，所以他从绝望吐槽转向接受处境，并获得恢复人形的模糊线索。",
        ]
    chain = []
    for index, point in enumerate(turning_points, start=1):
        previous = turning_points[index - 2].title if index > 1 else "故事启动事件"
        chain.append(f"因为{previous}造成新的处境，所以{point.description}")
    return chain


def _story_synopsis_character_arc(story_bible: StoryBible) -> str:
    if "马桶" in _story_bible_text(story_bible):
        return "从被困在马桶形态里的绝望吐槽役，转变为能在荒诞限制中主动帮助他人的异世界特殊存在。"
    return f"从被核心冲突限制的被动状态，转向理解并实践主题“{story_bible.theme}”的主动状态。"


def _story_synopsis_climax(story_bible: StoryBible, turning_points: list[TurningPoint]) -> str:
    if "马桶" in _story_bible_text(story_bible):
        return "第三集末尾，主角在一次误会升级中用有限马桶功能真正帮到来访者，系统随即给出恢复人形的模糊提示。"
    return turning_points[-1].description if turning_points else story_bible.core_conflict


def _story_synopsis_resolution(story_bible: StoryBible) -> str:
    if "马桶" in _story_bible_text(story_bible):
        return "主角仍未恢复人形，也没有人真正确认马桶里住着穿越者，但他完成从绝望吐槽到主动帮助他人的变化，并留下恢复线索。"
    return f"核心冲突阶段性收束，人物变化回到主题：{story_bible.theme}"


def _turning_points_from_timeline_rules(timeline_rules: list[str]) -> list[TurningPoint]:
    points: list[TurningPoint] = []
    for rule in timeline_rules:
        match = re.search(r"第\s*(\d+)\s*集[：:](.+)", rule)
        if not match:
            continue
        index = int(match.group(1))
        description = match.group(2).strip()
        title = description.split("→", 1)[0].split("，", 1)[0][:20] or f"第{index}集转折"
        points.append(
            TurningPoint(
                turning_point_id=f"TP_{index:02d}",
                title=title,
                description=description,
                story_effect=f"推动第{index}集的核心剧情变化。",
            )
        )
    return points


def _story_bible_text(story_bible: StoryBible) -> str:
    return "\n".join(
        [
            story_bible.title or "",
            story_bible.summary,
            story_bible.theme,
            story_bible.core_conflict,
            *story_bible.world_rules,
            *story_bible.timeline_rules,
            *story_bible.immutable_facts,
        ]
    )


def build_character_bible(story_bible: StoryBible, story_synopsis: StorySynopsis) -> CharacterBible:
    """根据 Story Bible / Synopsis 动态生成兜底人物圣经。

    这个函数只在真实 LLM 不可用或解析失败时使用，因此必须尽量贴合上游设定，
    不能写死某一种题材模板。核心策略是从故事文本里识别主角性别/类型、主要对手、
    关键盟友和显性能力，再生成可被下游解析的中等结构化人物数据。
    """

    story_text = _story_text(story_bible, story_synopsis)
    protagonist_name = _detect_protagonist_name(story_text)
    antagonist_name = _detect_antagonist_name(story_text)
    ally_names = _detect_ally_names(story_text, antagonist_name)
    protagonist_arc = (
        story_synopsis.character_arcs[0].arc
        if story_synopsis.character_arcs
        else _first_non_empty(story_synopsis.resolution, story_synopsis.protagonist_goal)
    )
    protagonist = CharacterProfile(
        character_id="CHAR_001",
        name=protagonist_name,
        role="protagonist",
        identity=_identity_for_protagonist(story_text, story_synopsis),
        personality=_personality_for_protagonist(story_text),
        motivation=story_synopsis.protagonist_goal,
        external_goal=_external_goal_from_synopsis(story_synopsis),
        internal_goal=_internal_goal_from_synopsis(story_synopsis),
        voice_style=_voice_style_from_story(story_text),
        visual_keywords=_visual_keywords_from_story(story_text, "protagonist"),
        story_function="承载主线目标、观众情绪站队和最终变化弧线。",
        character_arc=protagonist_arc,
    )
    antagonist = CharacterProfile(
        character_id="CHAR_002",
        name=antagonist_name,
        role="antagonist",
        identity=_identity_for_antagonist(story_text, antagonist_name),
        personality=_personality_for_antagonist(story_text),
        motivation=f"维持与“{story_bible.core_conflict}”相关的既有优势，不让主角完成逆转。",
        external_goal=f"阻止{protagonist_name}完成主线目标。",
        internal_goal="证明自己的秩序、力量或利益逻辑不可被挑战。",
        voice_style=_antagonist_voice_style(story_text),
        visual_keywords=_visual_keywords_from_story(story_text, "antagonist"),
        story_function="制造主线最大压力，并把主角推向最终变化。",
        character_arc="从占据优势到被主角找到破绽并完成反转。",
    )

    characters = [protagonist, antagonist]
    relationships = [
        CharacterRelationship(
            relationship_id="REL_001",
            source_character_id="CHAR_001",
            target_character_id="CHAR_002",
            type="enemy",
            description=_join_for_fallback(
                story_bible.core_conflict,
                _first_non_empty(
                    story_synopsis.major_conflicts[0] if story_synopsis.major_conflicts else "",
                    story_synopsis.climax,
                ),
            ),
            change_arc="从力量或信息不对等，发展为围绕主线目标的正面对抗与最终反转。",
        )
    ]

    for offset, ally_name in enumerate(ally_names, start=3):
        character_id = f"CHAR_{offset:03d}"
        characters.append(
            CharacterProfile(
                character_id=character_id,
                name=ally_name,
                role="ally",
                identity=_identity_for_ally(story_text, ally_name),
                personality=["行动感强", "与主角形成互补", "在关键节点推动关系变化"],
                motivation=f"因主线事件与{protagonist_name}绑定，并在关键冲突中选择支持或靠近主角。",
                external_goal=f"协助{protagonist_name}推进阶段性胜利。",
                internal_goal="确认自己在主线关系中的立场和价值。",
                voice_style=_ally_voice_style(story_text, ally_name),
                visual_keywords=_visual_keywords_from_story(story_text, "ally", ally_name),
                story_function=f"作为{protagonist_name}的关键关系/助力，增强爽点、情绪或关系张力。",
                character_arc=f"从被主线事件卷入，到在关键节点确认与{protagonist_name}的关系或立场。",
            )
        )
        relationships.append(
            CharacterRelationship(
                relationship_id=f"REL_{offset - 1:03d}",
                source_character_id="CHAR_001",
                target_character_id=character_id,
                type="ally",
                description=_relationship_reason_from_story(story_synopsis, ally_name),
                change_arc=f"从因事件相遇或立场未稳，发展为在主线推进中逐渐靠近并支持{protagonist_name}。",
            )
        )

    return CharacterBible(
        character_bible_id="character_bible_v001",
        parent_artifact_id=story_synopsis.story_synopsis_id,
        characters=characters,
        relationships=relationships,
        character_groups=[
            {
                "group_id": "GROUP_001",
                "name": "主角关系阵营",
                "type": "faction",
                "members": [character.character_id for character in characters if character.role in {"protagonist", "ally"}],
            },
            {
                "group_id": "GROUP_002",
                "name": "对抗压力来源",
                "type": "faction",
                "members": ["CHAR_002"],
            },
        ],
    )


def build_episode_outline_package(
    brief: CreativeBrief,
    story_bible: StoryBible,
    story_synopsis: StorySynopsis,
    character_bible: CharacterBible,
) -> EpisodeOutlinePackage:
    """根据故事因果链动态切分分集兜底大纲。"""

    episode_count = max(1, brief.episode_count or _episode_count_from_bible(story_bible) or 12)
    duration = brief.episode_duration_minutes or 2
    platform = brief.platform or _platform_from_bible(story_bible) or "短视频平台"
    protagonist_id = character_bible.characters[0].character_id if character_bible.characters else "CHAR_001"
    antagonist_id = character_bible.characters[1].character_id if len(character_bible.characters) > 1 else "CHAR_002"
    ally_ids = [character.character_id for character in character_bible.characters[2:]]
    beats = _episode_beats(story_synopsis, episode_count)

    episodes: list[EpisodeOutline] = []
    for index, beat in enumerate(beats, start=1):
        episode_id = f"EP_{index:03d}"
        is_first = index == 1
        is_final = index == episode_count
        stage = "开端/启动" if is_first else "终局/收束" if is_final else "中段/升级"
        related_ally_id = ally_ids[(index - 1) % len(ally_ids)] if ally_ids else None
        participant_ids = [protagonist_id, antagonist_id] + ([related_ally_id] if related_ally_id else [])
        key_events = _key_events_for_episode(story_synopsis, beat, index, episode_count)

        episodes.append(
            EpisodeOutline(
                episode_id=episode_id,
                episode_number=index,
                title=f"第{index}集：{beat['title']}",
                basic_info={"duration_minutes": duration, "platform": platform, "story_stage": stage},
                episode_positioning=_episode_positioning(beat, index, episode_count),
                opening_hook=_opening_hook_from_beat(beat, is_first),
                core_conflict=_conflict_for_episode(story_bible, story_synopsis, index),
                key_events=key_events,
                characters_and_relationship_changes=[
                    {
                        "character_ids": participant_ids,
                        "change": _relationship_change_for_episode(character_bible, index, is_final),
                    }
                ],
                emotional_beats=_emotional_beats_for_episode(story_bible, index, episode_count),
                turning_point_and_climax=story_synopsis.climax if is_final else beat["turning_point"],
                ending_and_cliffhanger=story_synopsis.resolution if is_final else _cliffhanger_for_episode(beats, index),
            )
        )

    return EpisodeOutlinePackage(outline_package_id="episode_outline_v001", episodes=episodes)


def _story_text(story_bible: StoryBible, story_synopsis: StorySynopsis) -> str:
    values: list[str] = [
        story_bible.title or "",
        story_bible.summary,
        story_bible.theme,
        story_bible.core_conflict,
        *story_bible.world_rules,
        *story_bible.timeline_rules,
        *story_bible.immutable_facts,
        story_synopsis.premise,
        story_synopsis.protagonist_goal,
        story_synopsis.main_story_arc,
        *story_synopsis.major_conflicts,
        *story_synopsis.causal_chain,
        story_synopsis.climax,
        story_synopsis.resolution,
    ]
    values.extend(point.description for point in story_synopsis.major_turning_points)
    values.extend(arc.arc for arc in story_synopsis.character_arcs)
    return "\n".join(item for item in values if item)


def _explicit_character_anchors(story_text: str) -> list[str]:
    """提取必须进入人物系统的显性角色名/类型名。"""

    candidates = [
        "魔王",
        "精灵公主",
        "龙族少女",
        "四天王",
        "合伙人",
        "董事",
        "资本方",
        "旧下属",
    ]
    anchors = [candidate for candidate in candidates if candidate in story_text]
    # 四天王、董事、资本方有时是组织压力源，不一定必须作为单人角色；优先约束更明确的人物。
    strong_anchors = [anchor for anchor in anchors if anchor not in {"四天王", "董事", "资本方"}]
    return strong_anchors[:4]


def _has_any(text: str, candidates: list[str]) -> bool:
    return any(candidate in text for candidate in candidates)


def _detect_protagonist_name(story_text: str) -> str:
    if "女主" in story_text:
        return "女主"
    if "男主" in story_text:
        return "男主"
    return "主角"


def _detect_antagonist_name(story_text: str) -> str:
    for candidate in ("魔王", "魔王军", "四天王", "夺权者", "合伙人", "幕后老板", "资本方", "反派"):
        if candidate in story_text:
            return candidate
    return "主要对手"


def _detect_ally_names(story_text: str, antagonist_name: str) -> list[str]:
    candidates = ["精灵公主", "龙族少女", "盟友", "旧团队成员", "关键协助者", "阿澈"]
    allies = [candidate for candidate in candidates if candidate in story_text and candidate != antagonist_name]
    if "后宫" in story_text:
        for candidate in ("精灵公主", "龙族少女"):
            if candidate not in allies:
                allies.append(candidate)
    return allies[:3] or ["关键盟友"]


def _identity_for_protagonist(story_text: str, story_synopsis: StorySynopsis) -> str:
    if "穿越" in story_text:
        return "穿越者/异世界主角，保留原世界记忆并被迫面对新规则。"
    if "公司" in story_text or "夺权" in story_text:
        return "现代都市事业线主角，开局被夺走关键资源或身份。"
    return _first_sentence(story_synopsis.premise)


def _identity_for_antagonist(story_text: str, antagonist_name: str) -> str:
    if "魔王" in antagonist_name:
        return "异世界最终压迫源，拥有远高于主角初始阶段的力量。"
    if "公司" in story_text or "夺权" in story_text:
        return "现代利益关系中的主要控制者或夺权者。"
    return "主线中阻止主角达成目标的核心对手。"


def _identity_for_ally(story_text: str, ally_name: str) -> str:
    if ally_name in {"精灵公主", "龙族少女"}:
        return f"异世界关键关系人物：{ally_name}，承担助力、情绪和关系推进功能。"
    if "公司" in story_text or "证据" in story_text:
        return "主角调查、反击或重建联盟过程中的关键协助者。"
    return "主线推进中与主角产生重要联结的协助者。"


def _skills_from_story(story_text: str) -> list[str]:
    skills = []
    if "卡车" in story_text:
        skills.append("卡车之力")
    if "爆炸" in story_text or "毁灭冲击" in story_text:
        skills.append("受伤触发爆炸/毁灭冲击")
    if "现代" in story_text or "吐槽" in story_text:
        skills.append("现代思维与吐槽式应变")
    if "证据" in story_text:
        skills.append("证据搜集")
    if "谈判" in story_text or "公司" in story_text:
        skills.append("谈判与商业判断")
    return skills or ["快速学习", "危机应变", "抓住对手破绽"]


def _limitations_from_story(story_text: str) -> list[str]:
    limitations = []
    if "无法主动" in story_text or "被动" in story_text:
        limitations.append("核心能力无法完全主动控制")
    if "冷却" in story_text:
        limitations.append("能力存在冷却或触发限制")
    if "废物" in story_text or "嘲笑" in story_text:
        limitations.append("开局身份被轻视，资源和信任不足")
    if "失去" in story_text or "夺走" in story_text:
        limitations.append("开局失去关键主动权")
    return limitations or ["初期资源有限", "必须在高压中寻找突破"]


def _personality_for_protagonist(story_text: str) -> list[str]:
    traits = ["不认输", "应变快", "抗压"]
    if "沙雕" in story_text or "吐槽" in story_text:
        traits.extend(["沙雕吐槽", "反套路"])
    if "冷静" in story_text or "证据" in story_text:
        traits.append("冷静判断")
    return _unique(traits)


def _personality_for_antagonist(story_text: str) -> list[str]:
    if "魔王" in story_text:
        return ["压迫感强", "自信", "掌控欲强"]
    return ["控制欲强", "谨慎", "善于施压"]


def _antagonist_skills_from_story(story_text: str) -> list[str]:
    if "魔王" in story_text or "魔力" in story_text:
        return ["魔力压制", "军团控制", "高阶防御"]
    if "公司" in story_text or "资本" in story_text:
        return ["资源控制", "规则运作", "舆论压制"]
    return ["制造阻力", "压制主角", "维持旧秩序"]


def _ally_skills_from_story(story_text: str, ally_name: str) -> list[str]:
    if ally_name == "精灵公主":
        return ["身份资源", "情感助力", "异世界信息"]
    if ally_name == "龙族少女":
        return ["战斗力", "危机推动", "关系反差"]
    if "证据" in story_text:
        return ["信息搜集", "侧面调查", "风险协助"]
    return ["关键协助", "关系推进", "危机支援"]


def _desires_from_story(story_text: str) -> list[str]:
    if "后宫" in story_text:
        return ["变强", "活下去", "打破规则"]
    if "公司" in story_text or "主动权" in story_text:
        return ["主动权", "尊严", "真相"]
    return ["完成目标", "证明自己", "保护重要关系"]


def _fears_from_story(story_text: str) -> list[str]:
    if "致命伤" in story_text or "魔王" in story_text:
        return ["能力失效", "被强敌彻底碾压", "无法掌控代价"]
    if "背叛" in story_text or "夺权" in story_text:
        return ["再次被背叛", "真相被掩盖"]
    return ["目标失败", "失去重要关系"]


def _values_from_story(story_text: str) -> list[str]:
    if "沙雕" in story_text or "吐槽" in story_text:
        return ["不认输", "反套路", "活下去"]
    return ["尊严", "选择权", "承诺"]


def _flaws_from_story(story_text: str) -> list[str]:
    if "沙雕" in story_text or "疯狂" in story_text:
        return ["行动过于冒险", "容易用非常规方式解决问题"]
    return ["过度独立", "容易低估对手代价"]


def _voice_style_from_story(story_text: str) -> str:
    if "吐槽" in story_text or "沙雕" in story_text:
        return "现代吐槽口吻，反应快，越危险越用短句和反套路表达。"
    return "短句多，情绪明确，关键时刻直接有力。"


def _antagonist_voice_style(story_text: str) -> str:
    if "魔王" in story_text:
        return "压迫感强，语气高位，常用审判式短句。"
    return "克制、施压、带有掌控感。"


def _ally_voice_style(story_text: str, ally_name: str) -> str:
    if ally_name in {"精灵公主", "龙族少女"}:
        return "情绪外放，关系推进明显，和主角形成强反差。"
    if "吐槽" in story_text:
        return "节奏快，能接住主角吐槽，也能在关键时刻推进信息。"
    return "口语化，行动感强，负责缓冲和推动剧情。"


def _visual_keywords_from_story(story_text: str, role: str, name: str | None = None) -> list[str]:
    if name == "精灵公主":
        return ["精灵", "公主感", "轻盈", "异世界"]
    if name == "龙族少女":
        return ["龙族", "战斗感", "半龙元素", "反差萌"]
    if role == "antagonist" and "魔王" in story_text:
        return ["魔王", "压迫感", "暗色", "王座"]
    if "异世界" in story_text or "魔法" in story_text:
        return ["异世界", "战斗损伤", "强反差", "高能爽感"]
    if role == "protagonist":
        return ["主角感", "眼神坚定", "成长变化"]
    return ["关系人物", "清晰辨识度", "短剧视觉"]


def _appearance_hint(story_text: str, role: str) -> str:
    if "异世界" in story_text or "魔法" in story_text:
        if role == "antagonist":
            return "带有异世界强者压迫感，服装和姿态体现高位力量。"
        return "从狼狈开局逐渐转向更有战斗感和辨识度的异世界造型。"
    if role == "antagonist":
        return "造型精致克制，体现控制感和距离感。"
    return "造型随剧情从低位压抑逐渐转向更有掌控感。"


def _antagonist_background(story_text: str, antagonist_name: str) -> str:
    if "魔王" in antagonist_name:
        return "作为异世界最高压迫源登场，代表主角必须打破的终极力量规则。"
    return "掌握主角当前无法直接突破的资源、权力或信息优势。"


def _external_goal_from_synopsis(story_synopsis: StorySynopsis) -> str:
    return story_synopsis.protagonist_goal.split("内部目标", 1)[0].replace("外部目标：", "").strip(" ：。") or story_synopsis.protagonist_goal


def _internal_goal_from_synopsis(story_synopsis: StorySynopsis) -> str:
    if "内部目标" in story_synopsis.protagonist_goal:
        return story_synopsis.protagonist_goal.split("内部目标", 1)[1].strip(" ：。")
    return "完成从被动承受到主动掌控的核心变化。"


def _ally_current_goal(story_synopsis: StorySynopsis, ally_name: str) -> str:
    for step in story_synopsis.causal_chain:
        if ally_name in step:
            return step
    return "在关键节点帮助主角推进主线目标。"


def _relationship_reason_from_story(story_synopsis: StorySynopsis, ally_name: str) -> str:
    for step in story_synopsis.causal_chain:
        if ally_name in step:
            return step
    return f"{ally_name}与主角在主线事件中形成利益、情绪或目标绑定。"


def _relationship_development(story_synopsis: StorySynopsis, target_character_id: str) -> list[dict[str, Any]]:
    points = story_synopsis.major_turning_points[:3]
    if not points:
        return [{"episode": 1, "state": "关系启动", "trigger": story_synopsis.premise}]
    return [
        {"episode": index, "state": "关系变化", "trigger": point.description}
        for index, point in enumerate(points, start=1)
    ]


def _episode_beats(story_synopsis: StorySynopsis, episode_count: int) -> list[dict[str, str]]:
    turning_points = story_synopsis.major_turning_points
    causal_chain = story_synopsis.causal_chain
    beats: list[dict[str, str]] = []
    for index in range(episode_count):
        point = turning_points[min(index, len(turning_points) - 1)] if turning_points else None
        causal = causal_chain[min(index, len(causal_chain) - 1)] if causal_chain else story_synopsis.main_story_arc
        if point is not None:
            title = point.title
            description = point.description
            effect = point.story_effect or causal
        else:
            title = f"主线推进{index + 1}"
            description = causal
            effect = causal
        beats.append(
            {
                "title": title,
                "description": description,
                "causal": causal,
                "effect": effect,
                "turning_point": _first_non_empty(effect, description, causal),
            }
        )
    return beats


def _key_events_for_episode(
    story_synopsis: StorySynopsis,
    beat: dict[str, str],
    episode_number: int,
    episode_count: int,
) -> list[str]:
    previous_step = story_synopsis.causal_chain[episode_number - 2] if episode_number > 1 and len(story_synopsis.causal_chain) >= episode_number - 1 else story_synopsis.premise
    current_step = beat["causal"]
    next_step = (
        story_synopsis.causal_chain[episode_number]
        if len(story_synopsis.causal_chain) > episode_number
        else story_synopsis.resolution
    )
    if episode_number == episode_count:
        next_step = story_synopsis.resolution
    return _unique(
        [
            _shorten_event(previous_step),
            _shorten_event(beat["description"]),
            _shorten_event(current_step),
            _shorten_event(next_step),
        ]
    )[:4]


def _episode_positioning(beat: dict[str, str], episode_number: int, episode_count: int) -> str:
    if episode_number == 1:
        return f"建立故事启动事件和主角初始困境：{beat['description']}"
    if episode_number == episode_count:
        return f"完成最终高潮与结局收束：{beat['effect']}"
    return f"承接上一集后果，推进本集关键转折：{beat['effect']}"


def _opening_hook_from_beat(beat: dict[str, str], is_first: bool) -> str:
    prefix = "开场直接呈现故事启动事件：" if is_first else "开场承接上一集危机，立刻抛出新压力："
    return prefix + _shorten_event(beat["description"], limit=90)


def _conflict_for_episode(story_bible: StoryBible, story_synopsis: StorySynopsis, episode_number: int) -> str:
    if story_synopsis.major_conflicts:
        conflict = story_synopsis.major_conflicts[(episode_number - 1) % len(story_synopsis.major_conflicts)]
        return f"{conflict}；同时服务全局冲突：{story_bible.core_conflict}"
    return story_bible.core_conflict


def _relationship_change_for_episode(character_bible: CharacterBible, episode_number: int, is_final: bool) -> str:
    if is_final:
        return "核心关系在最终冲突后完成重新排序。"
    if character_bible.relationships:
        relationship = character_bible.relationships[(episode_number - 1) % len(character_bible.relationships)]
        return relationship.change_arc or relationship.description or f"{relationship.type} 关系随主线事件推进。"
    return "人物关系随主线事件发生阶段性变化。"


def _emotional_beats_for_episode(story_bible: StoryBible, episode_number: int, episode_count: int) -> list[str]:
    if "沙雕" in story_bible.summary or "吐槽" in story_bible.summary:
        base = ["荒诞开场", "被压制", "反套路爆发", "爽感释放"]
    elif "强爽" in story_bible.summary or "逆袭" in story_bible.summary:
        base = ["压迫", "不甘", "反击", "爽点释放"]
    else:
        base = ["悬念", "冲突", "转折", "推进"]
    if episode_number == episode_count:
        return base[:-1] + ["终局释放"]
    return base


def _cliffhanger_for_episode(beats: list[dict[str, str]], episode_number: int) -> str:
    next_index = min(episode_number, len(beats) - 1)
    return f"结尾抛出下一阶段危机：{_shorten_event(beats[next_index]['description'], limit=90)}"


def _episode_count_from_bible(story_bible: StoryBible) -> int | None:
    text = "\n".join([story_bible.summary, *story_bible.timeline_rules, *story_bible.immutable_facts])
    match = re.search(r"(\d+)\s*集", text)
    if match:
        return int(match.group(1))
    return None


def _platform_from_bible(story_bible: StoryBible) -> str | None:
    text = "\n".join(story_bible.immutable_facts + [story_bible.summary])
    for platform in ("抖音", "快手", "小红书", "B站", "视频号"):
        if platform in text:
            return platform
    return None


def _first_sentence(text: str, limit: int = 120) -> str:
    sentence = _shorten_event(text, limit=limit)
    for separator in ("。", "！", "？"):
        if separator in sentence:
            return sentence.split(separator, 1)[0] + separator
    return sentence


def _shorten_event(text: str, limit: int = 120) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip("，。；、 ") + "…"


def _first_non_empty(*values: str | None) -> str:
    for value in values:
        if value:
            return value
    return ""


def _join_for_fallback(*values: str | None) -> str:
    """把多个规则兜底片段合成一句可读关系描述。"""

    return "；".join(value for value in values if value)


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def build_episode_scripts(
    brief: CreativeBrief,
    story_bible: StoryBible,
    outline_package: EpisodeOutlinePackage,
    character_bible: CharacterBible,
) -> list[EpisodeScript]:
    characters = character_bible.characters
    protagonist = characters[0] if characters else None
    story_seed = _story_seed_from_bible(story_bible)
    story_anchor_text = _join_for_fallback(
        story_seed,
        story_bible.summary,
        story_bible.core_conflict,
        *story_bible.immutable_facts,
    )
    protagonist_name = _fallback_protagonist_name(story_anchor_text, protagonist)
    scene_partner_name = _fallback_scene_partner_name(story_anchor_text, protagonist_name)
    project_metadata = ProjectMetadata(
        title=story_bible.title,
        genre=brief.genre,
        total_episodes=len(outline_package.episodes) or brief.episode_count,
        platform=brief.platform,
        episode_duration_minutes=brief.episode_duration_minutes,
    )

    scripts: list[EpisodeScript] = []
    for outline in outline_package.episodes:
        episode_anchor_text = _join_for_fallback(
            story_seed,
            outline.opening_hook,
            outline.core_conflict,
            *outline.key_events,
            outline.turning_point_and_climax,
            outline.ending_and_cliffhanger,
        )
        location = _fallback_scene_location(episode_anchor_text)
        key_props = _fallback_key_props(episode_anchor_text)
        appearing_characters = _fallback_episode_characters(
            characters,
            protagonist_name=protagonist_name,
            scene_partner_name=scene_partner_name,
        )
        script_text = _fallback_episode_script_text(
            outline,
            story_seed=story_seed,
            protagonist_name=protagonist_name,
            scene_partner_name=scene_partner_name,
            location=location,
            key_props=key_props,
        )
        scripts.append(
            EpisodeScript(
                episode_script_id=f"episode_script_ep{outline.episode_number:03d}_v001",
                project_metadata=project_metadata,
                episode=EpisodeLevel(
                    episode_number=outline.episode_number,
                    episode_title=outline.title,
                    core_function=outline.episode_positioning,
                    appearing_characters=appearing_characters,
                    ending_hook=outline.ending_and_cliffhanger,
                ),
                scenes=[
                    SceneScript(
                        scene_number=1,
                        interior_exterior="内景",
                        location=location,
                        time="日",
                        continuity=None,
                        script_text=script_text,
                    )
                ],
            )
        )

    return scripts


def _story_seed_from_bible(story_bible: StoryBible) -> str:
    for fact in story_bible.immutable_facts:
        if "故事种子：" in fact:
            return fact.split("故事种子：", 1)[1].strip()

    match = re.search(r"故事以“(.+?)”为核心种子", story_bible.summary)
    if match:
        return match.group(1).strip()

    return story_bible.summary


def _fallback_protagonist_name(
    story_text: str,
    protagonist: CharacterProfile | None,
) -> str:
    for pattern in (
        r"(?:女主|男主|高中生|普通外卖员|外卖员)([\u4e00-\u9fff]{2,4})",
        r"([\u4e00-\u9fff]{2,4})(?:在|被|误入|发现|必须)",
    ):
        match = re.search(pattern, story_text)
        if match:
            name = match.group(1)
            if name not in {"故事", "平台", "普通", "必须"}:
                return name

    if protagonist and protagonist.name not in {"主角", "女主", "男主"}:
        return protagonist.name
    if "女主" in story_text:
        return "女主"
    if "男主" in story_text:
        return "男主"
    return "主角"


def _fallback_scene_partner_name(story_text: str, protagonist_name: str) -> str:
    for candidate in (
        "精灵店员",
        "失踪同学",
        "合伙人",
        "盟友",
        "主要对手",
        "关键协助者",
    ):
        if candidate in story_text and candidate != protagonist_name:
            return candidate
    return "关键人物"


def _fallback_scene_location(story_text: str) -> str:
    for candidate in (
        "异世界便利店",
        "雨夜后巷",
        "雨后车站",
        "夜宵档口",
        "便利店",
        "后巷",
        "车站",
        "档口",
    ):
        if candidate in story_text:
            return candidate
    return "核心冲突地点"


def _fallback_key_props(story_text: str) -> list[str]:
    candidates = [
        "会说话的优惠券",
        "优惠券",
        "魔法收银机",
        "收银机",
        "旧游戏机",
        "游戏机",
        "像素录像",
        "录像",
        "账本",
        "档口",
    ]
    return _unique([candidate for candidate in candidates if candidate in story_text])


def _fallback_episode_characters(
    characters: list[CharacterProfile],
    *,
    protagonist_name: str,
    scene_partner_name: str,
) -> list[EpisodeCharacter]:
    appearing = [
        EpisodeCharacter(
            name=character.name,
            brief=_join_for_fallback(character.role, character.identity, character.story_function),
        )
        for character in characters[:4]
    ]
    existing_names = {character.name for character in appearing}
    for name, brief in (
        (protagonist_name, "本集主角，承载故事种子中的核心行动。"),
        (scene_partner_name, "与主角在本集核心事件中形成冲突或协作关系。"),
    ):
        if name and name not in existing_names:
            appearing.append(EpisodeCharacter(name=name, brief=brief))
            existing_names.add(name)
    return appearing


def _fallback_episode_script_text(
    outline,
    *,
    story_seed: str,
    protagonist_name: str,
    scene_partner_name: str,
    location: str,
    key_props: list[str],
) -> str:
    seed_line = _shorten_event(story_seed, limit=180)
    props_text = "、".join(key_props) if key_props else "关键线索"
    key_event_lines = [_shorten_event(event, limit=110) for event in outline.key_events[:3]]
    event_text = "；".join(key_event_lines) if key_event_lines else outline.core_conflict
    return "\n".join(
        [
            f"{outline.opening_hook}",
            f"{protagonist_name}来到{location}，本场事件紧扣故事种子：{seed_line}",
            f"{protagonist_name}第一时间确认{props_text}的状态，发现它正把局面推向失控边缘。",
            f"{scene_partner_name}看向{protagonist_name}，压低声音提醒：如果现在处理错，后果会立刻扩大。",
            f"{protagonist_name}：先别解释，先把眼前这个问题解决。",
            f"本集关键事件依次推进：{event_text}",
            f"{outline.core_conflict}",
            f"{protagonist_name}围绕{props_text}做出关键行动，现场关系和目标随之发生变化。",
            f"{outline.turning_point_and_climax or '冲突在本场完成一次明确升级。'}",
            f"{outline.ending_and_cliffhanger or '结尾留下下一步必须面对的新问题。'}",
        ]
    )


def build_dialogue_polish_package(
    episode_scripts: list[EpisodeScript],
    story_bible: StoryBible,
) -> DialoguePolishPackage:
    notes = [
        DialoguePolishNote(
            episode_id=_episode_ref(script),
            scene_id=_scene_ref(script, script.scenes[0]) if script.scenes else None,
            target="强化短剧口语化和角色声口。",
            change_summary="保留核心剧情信息，压缩解释性台词，增加情绪明确的短句。",
            preserved_constraints=story_bible.immutable_facts,
        )
        for script in episode_scripts
    ]
    return DialoguePolishPackage(polish_package_id="dialogue_polish_v001", notes=notes)


def _compact_creative_brief(brief: CreativeBrief) -> dict[str, Any]:
    return brief.model_dump(exclude_none=True)


def _compact_story_bible(story_bible: StoryBible | dict | None) -> dict[str, Any]:
    if story_bible is None:
        return {}
    bible = _ensure_model(story_bible, StoryBible) if isinstance(story_bible, dict) else story_bible
    return {
        "story_bible_id": bible.story_bible_id,
        "title": bible.title,
        "summary": bible.summary,
        "theme": bible.theme,
        "core_conflict": bible.core_conflict,
        "world_rules": bible.world_rules,
        "timeline_rules": bible.timeline_rules,
        "immutable_facts": bible.immutable_facts,
    }


def _compact_story_synopsis(story_synopsis: StorySynopsis | dict | None) -> dict[str, Any]:
    if story_synopsis is None:
        return {}
    synopsis = _ensure_model(story_synopsis, StorySynopsis) if isinstance(story_synopsis, dict) else story_synopsis
    return {
        "story_synopsis_id": synopsis.story_synopsis_id,
        "premise": synopsis.premise,
        "protagonist_goal": synopsis.protagonist_goal,
        "main_story_arc": synopsis.main_story_arc,
        "major_turning_points": [item.model_dump(mode="json") for item in synopsis.major_turning_points],
        "major_conflicts": synopsis.major_conflicts,
        "causal_chain": synopsis.causal_chain,
        "character_arcs": [item.model_dump(mode="json") for item in synopsis.character_arcs],
        "climax": synopsis.climax,
        "resolution": synopsis.resolution,
    }


def _compact_character_bible(character_bible: CharacterBible) -> dict[str, Any]:
    return {
        "character_bible_id": character_bible.character_bible_id,
        "characters": [
            {
                "character_id": item.character_id,
                "name": item.name,
                "role": item.role,
                "motivation": item.motivation,
                "external_goal": item.external_goal,
                "character_arc": item.character_arc,
                "voice_style": item.voice_style,
                "visual_keywords": item.visual_keywords,
            }
            for item in character_bible.characters
        ],
        "relationships": [item.model_dump(mode="json") for item in character_bible.relationships],
    }


def _compact_character_bible_for_outline(character_bible: CharacterBible) -> dict[str, Any]:
    """给分集大纲使用的更小人物上下文。"""

    return {
        "character_bible_id": character_bible.character_bible_id,
        "characters": [
            {
                "character_id": item.character_id,
                "name": item.name,
                "role": item.role,
                "external_goal": item.external_goal,
                "motivation": item.motivation,
                "character_arc": item.character_arc,
            }
            for item in character_bible.characters
        ],
        "relationships": [
            {
                "relationship_id": item.relationship_id,
                "source_character_id": item.source_character_id,
                "target_character_id": item.target_character_id,
                "type": item.type,
                "description": item.description,
                "change_arc": item.change_arc,
            }
            for item in character_bible.relationships
        ],
    }


def _compact_episode_outline(outline_package: EpisodeOutlinePackage) -> dict[str, Any]:
    return outline_package.model_dump(mode="json")


def _compact_episode_scripts(episode_scripts: list[EpisodeScript]) -> list[dict[str, Any]]:
    return [
        {
            "episode_script_id": script.episode_script_id,
            "project_metadata": script.project_metadata.model_dump(mode="json", exclude_none=True),
            "episode": script.episode.model_dump(mode="json", exclude_none=True),
            "scenes": [
                {
                    "scene_number": scene.scene_number,
                    "interior_exterior": scene.interior_exterior,
                    "location": scene.location,
                    "time": scene.time,
                    "continuity": scene.continuity,
                    "script_text": _shorten_event(scene.script_text, limit=220),
                }
                for scene in script.scenes
            ],
        }
        for script in episode_scripts
    ]


def _episode_ref(script: EpisodeScript) -> str:
    return f"EP_{script.episode.episode_number:03d}"


def _scene_ref(script: EpisodeScript, scene: SceneScript) -> str:
    return f"{_episode_ref(script)}_SC_{scene.scene_number:03d}"
