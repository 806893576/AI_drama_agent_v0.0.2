"""Human confirmation revision and approval service."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, TypeAdapter

from domain.brief.schemas import CreativeBrief
from domain.brief.validators import evaluate_brief_gate, validate_brief
from domain.human_confirmation import (
    BRIEF_CONFIRMATION_POINT,
    EPISODE_OUTLINE_CONFIRMATION_POINT,
    STYLE_CONFIRMATION_POINT,
    HumanConfirmationPoint,
)
from domain.story.episode_outline import EpisodeOutlinePackage
from domain.style import CreativeStyleGuide
from graph.nodes.style_guide_node import render_style_guide_context
from memory.checkpoint import JsonCheckpointStore
from schemas.enums import ArtifactType, NodeId
from services.llm import (
    generate_model_with_fallback,
    json_dumps_for_prompt,
    llm_trace_context,
    render_creative_brief_context,
    structured_output_mode,
)
from services.storage.artifact_store import ArtifactStore
from state.artifact_refs import ArtifactRef, coerce_artifact_ref


@dataclass(frozen=True, slots=True)
class HumanConfirmationUpdate:
    state: dict[str, Any]
    revised_artifact_key: str | None = None
    revised_artifact_id: str | None = None
    message: str = ""


@dataclass(frozen=True, slots=True)
class EditableArtifact:
    artifact_key: str
    ref: ArtifactRef
    content: Any


POINT_ARTIFACT_KEYS: dict[str, str] = {
    BRIEF_CONFIRMATION_POINT: "creative_brief",
    STYLE_CONFIRMATION_POINT: "style_guide",
    EPISODE_OUTLINE_CONFIRMATION_POINT: "episode_outline",
}

POINT_MODEL_TYPES: dict[str, Any] = {
    BRIEF_CONFIRMATION_POINT: CreativeBrief,
    STYLE_CONFIRMATION_POINT: CreativeStyleGuide,
    EPISODE_OUTLINE_CONFIRMATION_POINT: EpisodeOutlinePackage,
}

POINT_ARTIFACT_TYPES: dict[str, ArtifactType] = {
    BRIEF_CONFIRMATION_POINT: ArtifactType.CREATIVE_BRIEF,
    STYLE_CONFIRMATION_POINT: ArtifactType.STYLE_GUIDE,
    EPISODE_OUTLINE_CONFIRMATION_POINT: ArtifactType.EPISODE_OUTLINE,
}

POINT_NODE_IDS: dict[str, NodeId] = {
    BRIEF_CONFIRMATION_POINT: NodeId.HUMAN_BRIEF_CONFIRM,
    STYLE_CONFIRMATION_POINT: NodeId.HUMAN_STYLE_CONFIRM,
    EPISODE_OUTLINE_CONFIRMATION_POINT: NodeId.HUMAN_EPISODE_OUTLINE_CONFIRM,
}

POINT_PROMPT_IDS: dict[str, str] = {
    BRIEF_CONFIRMATION_POINT: "human_revision.brief",
    STYLE_CONFIRMATION_POINT: "human_revision.style",
    EPISODE_OUTLINE_CONFIRMATION_POINT: "human_revision.episode_outline",
}


class EpisodeOutlineItemPatch(BaseModel):
    episode_id: str | None = None
    episode_number: int
    title: str | None = None
    basic_info: dict[str, Any] | None = None
    episode_positioning: str | None = None
    opening_hook: str | None = None
    core_conflict: str | None = None
    key_events: list[str] | None = None
    characters_and_relationship_changes: list[dict[str, Any]] | None = None
    emotional_beats: list[str] | None = None
    turning_point_and_climax: str | None = None
    ending_and_cliffhanger: str | None = None


class EpisodeOutlinePatch(BaseModel):
    revision_notes: str | None = None
    episodes: list[EpisodeOutlineItemPatch] = Field(default_factory=list)

DOWNSTREAM_STATE_KEYS: dict[str, set[str]] = {
    BRIEF_CONFIRMATION_POINT: {
        "style_guide",
        "style_guide_summary",
        "story_bible",
        "story_synopsis",
        "character_bible",
        "episode_outline_package",
        "episode_scripts",
        "dialogue_polish_package",
        "writer_package",
        "writer_subgraph_completed",
        "script_review_report",
        "quality_score_report",
        "script_safety_report",
        "text_continuity_report",
        "scene_breakdowns",
        "shot_designs",
        "performance_direction",
        "audiovisual_enhanced_shot_list",
        "director_package",
        "audiovisual_package",
        "shot_av_safety_report",
        "art_prompt_package",
        "prompt_safety_report",
        "asset_registry",
        "production_continuity_report",
        "final_safety_report",
        "final_acceptance_report",
        "final_package",
    },
    STYLE_CONFIRMATION_POINT: {
        "story_bible",
        "story_synopsis",
        "character_bible",
        "episode_outline_package",
        "episode_scripts",
        "dialogue_polish_package",
        "writer_package",
        "writer_subgraph_completed",
        "script_review_report",
        "quality_score_report",
        "script_safety_report",
        "text_continuity_report",
        "scene_breakdowns",
        "shot_designs",
        "performance_direction",
        "audiovisual_enhanced_shot_list",
        "director_package",
        "audiovisual_package",
        "shot_av_safety_report",
        "art_prompt_package",
        "prompt_safety_report",
        "asset_registry",
        "production_continuity_report",
        "final_safety_report",
        "final_acceptance_report",
        "final_package",
    },
    EPISODE_OUTLINE_CONFIRMATION_POINT: {
        "episode_scripts",
        "dialogue_polish_package",
        "writer_package",
        "writer_subgraph_completed",
        "script_review_report",
        "quality_score_report",
        "script_safety_report",
        "text_continuity_report",
        "scene_breakdowns",
        "shot_designs",
        "performance_direction",
        "audiovisual_enhanced_shot_list",
        "director_package",
        "audiovisual_package",
        "shot_av_safety_report",
        "art_prompt_package",
        "prompt_safety_report",
        "asset_registry",
        "production_continuity_report",
        "final_safety_report",
        "final_acceptance_report",
        "final_package",
    },
}

DOWNSTREAM_ARTIFACT_KEYS: dict[str, set[str]] = {
    BRIEF_CONFIRMATION_POINT: {
        "style_guide",
        "story_bible",
        "story_synopsis",
        "character_bible",
        "episode_outline",
        "episode_script",
        "dialogue_polish",
        "writer_package",
        "script_review",
        "quality_score",
        "script_safety",
        "text_continuity",
        "scene_breakdown",
        "shot_list",
        "performance_direction",
        "audiovisual_enhanced_shot_list",
        "director_package",
        "audiovisual_package",
        "shot_av_safety",
        "art_package",
        "prompt_safety",
        "asset_registry",
        "production_continuity",
        "final_safety",
        "final_acceptance",
        "final_package",
    },
    STYLE_CONFIRMATION_POINT: {
        "story_bible",
        "story_synopsis",
        "character_bible",
        "episode_outline",
        "episode_script",
        "dialogue_polish",
        "writer_package",
        "script_review",
        "quality_score",
        "script_safety",
        "text_continuity",
        "scene_breakdown",
        "shot_list",
        "performance_direction",
        "audiovisual_enhanced_shot_list",
        "director_package",
        "audiovisual_package",
        "shot_av_safety",
        "art_package",
        "prompt_safety",
        "asset_registry",
        "production_continuity",
        "final_safety",
        "final_acceptance",
        "final_package",
    },
    EPISODE_OUTLINE_CONFIRMATION_POINT: {
        "episode_script",
        "dialogue_polish",
        "writer_package",
        "script_review",
        "quality_score",
        "script_safety",
        "text_continuity",
        "scene_breakdown",
        "shot_list",
        "performance_direction",
        "audiovisual_enhanced_shot_list",
        "director_package",
        "audiovisual_package",
        "shot_av_safety",
        "art_package",
        "prompt_safety",
        "asset_registry",
        "production_continuity",
        "final_safety",
        "final_acceptance",
        "final_package",
    },
}

DOWNSTREAM_COMPLETED_NODES: dict[str, set[str]] = {
    BRIEF_CONFIRMATION_POINT: {
        "style_guide",
        "human_style_confirm",
        "producer_router",
        "writer.story_bible",
        "writer.story_synopsis",
        "writer.character_bible",
        "writer.episode_outline",
        "human_episode_outline_confirm",
        "writer.episode_script",
        "writer.dialogue_polish",
        "writer.script_package",
        "script_reviewer",
        "quality_scoring",
        "script_safety",
        "text_continuity",
        "director.scene_breakdown",
        "director.shot_design",
        "director.performance",
        "director.package",
        "av.enhancement",
        "av.package",
        "shot_av_safety",
        "art_agent",
        "prompt_safety",
        "asset_manager",
        "production_continuity",
        "final_safety",
        "final_acceptance",
        "final_output",
    },
    STYLE_CONFIRMATION_POINT: {
        "producer_router",
        "writer.story_bible",
        "writer.story_synopsis",
        "writer.character_bible",
        "writer.episode_outline",
        "human_episode_outline_confirm",
        "writer.episode_script",
        "writer.dialogue_polish",
        "writer.script_package",
        "script_reviewer",
        "quality_scoring",
        "script_safety",
        "text_continuity",
        "director.scene_breakdown",
        "director.shot_design",
        "director.performance",
        "director.package",
        "av.enhancement",
        "av.package",
        "shot_av_safety",
        "art_agent",
        "prompt_safety",
        "asset_manager",
        "production_continuity",
        "final_safety",
        "final_acceptance",
        "final_output",
    },
    EPISODE_OUTLINE_CONFIRMATION_POINT: {
        "writer.episode_script",
        "writer.dialogue_polish",
        "writer.script_package",
        "script_reviewer",
        "quality_scoring",
        "script_safety",
        "text_continuity",
        "director.scene_breakdown",
        "director.shot_design",
        "director.performance",
        "director.package",
        "av.enhancement",
        "av.package",
        "shot_av_safety",
        "art_agent",
        "prompt_safety",
        "asset_manager",
        "production_continuity",
        "final_safety",
        "final_acceptance",
        "final_output",
    },
}


def load_editable_artifact(job_id: str, artifact_key: str) -> EditableArtifact:
    state = _load_checkpoint(job_id)
    refs = state.get("artifact_refs", {})
    if artifact_key not in refs:
        raise FileNotFoundError(f"Artifact key not found in checkpoint: {artifact_key}")
    ref = coerce_artifact_ref(refs[artifact_key])
    envelope = ArtifactStore().load(ref, job_id=job_id)
    return EditableArtifact(artifact_key=artifact_key, ref=ref, content=envelope.content)


def approve_human_confirmation(
    job_id: str,
    *,
    confirmation_point: HumanConfirmationPoint | None = None,
) -> HumanConfirmationUpdate:
    state = _load_checkpoint(job_id)
    point = _resolve_point(state, confirmation_point)
    confirmed = _confirmed_points_without(state, point)
    confirmed.append(point)
    state["confirmed_human_points"] = confirmed
    _clear_pause_flags(state)
    JsonCheckpointStore().save(job_id, state)
    return HumanConfirmationUpdate(state=state, message=f"{point} confirmation approved.")


def revise_human_confirmation(
    job_id: str,
    *,
    confirmation_point: HumanConfirmationPoint | None = None,
    mode: str,
    feedback: str | None = None,
    artifact_content: Any = None,
    llm_format_mode: str = "interrupt",
) -> HumanConfirmationUpdate:
    state = _load_checkpoint(job_id)
    point = _resolve_point(state, confirmation_point)
    artifact_key = POINT_ARTIFACT_KEYS[point]
    model_type = POINT_MODEL_TYPES[point]
    current = _current_model(state, artifact_key, model_type)

    if mode == "expert":
        if artifact_content is None:
            raise ValueError("artifact_content is required in expert mode.")
        revised = TypeAdapter(model_type).validate_python(artifact_content)
    elif mode == "normal":
        if not feedback or not feedback.strip():
            raise ValueError("feedback is required in normal mode.")
        revised = _revise_with_feedback(
            job_id=job_id,
            point=point,
            current=current,
            feedback=feedback.strip(),
            state=state,
            llm_format_mode=llm_format_mode,
        )
    else:
        raise ValueError(f"Unsupported human confirmation mode: {mode}")

    if point == EPISODE_OUTLINE_CONFIRMATION_POINT:
        _validate_episode_outline_against_brief(revised, state)

    store = ArtifactStore()
    artifact_type = POINT_ARTIFACT_TYPES[point]
    previous_ref = state.get("artifact_refs", {}).get(artifact_key)
    ref = store.save(
        job_id=job_id,
        artifact_type=artifact_type,
        content=revised,
        summary=_summary_for(point, revised),
        created_by=POINT_NODE_IDS[point],
        parent_ref=previous_ref,
    )
    _invalidate_downstream(state, point)
    state.setdefault("artifact_refs", {})[artifact_key] = ref
    _write_model_to_state(state, point, revised, ref)
    state["confirmed_human_points"] = _confirmed_points_without(state, point)
    state["human_confirmation_required"] = True
    state["human_confirmation_point"] = point
    state["editable_artifact_refs"] = {artifact_key: ref}
    state["final_output_ready"] = False
    state["final_message"] = f"{_title_for(point)}已保存修订版本，等待确认。"
    JsonCheckpointStore().save(job_id, state)
    return HumanConfirmationUpdate(
        state=state,
        revised_artifact_key=artifact_key,
        revised_artifact_id=ref.artifact_id,
        message=state["final_message"],
    )


def _load_checkpoint(job_id: str) -> dict[str, Any]:
    state = JsonCheckpointStore().load_or_none(job_id)
    if state is None:
        raise FileNotFoundError(f"Checkpoint not found: {job_id}")
    return state


def _resolve_point(
    state: dict[str, Any],
    confirmation_point: HumanConfirmationPoint | None,
) -> HumanConfirmationPoint:
    point = confirmation_point or state.get("human_confirmation_point")
    if point not in POINT_ARTIFACT_KEYS:
        raise ValueError(f"Unsupported or missing human confirmation point: {point}")
    active_point = state.get("human_confirmation_point")
    if active_point and confirmation_point and active_point != confirmation_point:
        raise ValueError(f"Active confirmation point is {active_point}, not {confirmation_point}.")
    return point


def _current_model(state: dict[str, Any], artifact_key: str, model_type: Any) -> Any:
    state_key = "episode_outline_package" if artifact_key == "episode_outline" else artifact_key
    current = state.get(state_key)
    if current is None:
        ref = state.get("artifact_refs", {}).get(artifact_key)
        if ref is None:
            raise FileNotFoundError(f"Artifact not found in state: {artifact_key}")
        current = ArtifactStore().load(ref, job_id=state["job_id"]).content
    return TypeAdapter(model_type).validate_python(current)


def _revise_with_feedback(
    *,
    job_id: str,
    point: str,
    current: Any,
    feedback: str,
    state: dict[str, Any],
    llm_format_mode: str,
) -> Any:
    if point == EPISODE_OUTLINE_CONFIRMATION_POINT:
        return _revise_episode_outline_with_feedback(
            job_id=job_id,
            current=TypeAdapter(EpisodeOutlinePackage).validate_python(current),
            feedback=feedback,
            state=state,
            llm_format_mode=llm_format_mode,
        )

    prompt_id = POINT_PROMPT_IDS[point]
    model_type = POINT_MODEL_TYPES[point]
    variables = {
        "current_artifact": json_dumps_for_prompt(current),
        "feedback": feedback,
        "guardrails": _guardrails_for(point, state),
    }
    with llm_trace_context(job_id), structured_output_mode(llm_format_mode):
        return generate_model_with_fallback(
            prompt_id,
            variables,
            model_type,
            fallback=lambda: _fallback_revision(point, current, feedback),
            temperature=0.2,
        )


def _revise_episode_outline_with_feedback(
    *,
    job_id: str,
    current: EpisodeOutlinePackage,
    feedback: str,
    state: dict[str, Any],
    llm_format_mode: str,
) -> EpisodeOutlinePackage:
    target_numbers = _extract_episode_numbers(feedback)
    variables = {
        "current_artifact": json_dumps_for_prompt(
            _episode_outline_patch_source(current, target_numbers)
        ),
        "context_summary": _episode_outline_revision_context(
            current,
            state,
            target_numbers=target_numbers,
        ),
        "feedback": feedback,
        "guardrails": _guardrails_for(EPISODE_OUTLINE_CONFIRMATION_POINT, state),
    }
    with llm_trace_context(job_id), structured_output_mode(llm_format_mode):
        patch = generate_model_with_fallback(
            POINT_PROMPT_IDS[EPISODE_OUTLINE_CONFIRMATION_POINT],
            variables,
            EpisodeOutlinePatch,
            fallback=lambda: _fallback_episode_outline_patch(feedback),
            temperature=0.2,
        )
    return _apply_episode_outline_patch(current, patch)


def _fallback_revision(point: str, current: Any, feedback: str) -> Any:
    data = current.model_dump(mode="json") if hasattr(current, "model_dump") else dict(current)
    note = f"人工修改意见：{feedback}"
    if point == BRIEF_CONFIRMATION_POINT:
        constraints = list(data.get("constraints") or [])
        constraints.append(note)
        data["constraints"] = constraints
        if data.get("story_seed"):
            data["story_seed"] = f"{data['story_seed']}；{note}"
        else:
            data["story_seed"] = note
        return CreativeBrief(**data)
    if point == STYLE_CONFIRMATION_POINT:
        style_do = data.get("style_do") or ""
        data["style_do"] = "；".join(part for part in [style_do, note] if part)
        return CreativeStyleGuide(**data)

    target_episode_number = _extract_episode_number(feedback)
    episodes = data.get("episodes") or []
    for episode in episodes:
        if target_episode_number is not None and episode.get("episode_number") != target_episode_number:
            continue
        key_events = list(episode.get("key_events") or [])
        key_events.append(note)
        episode["key_events"] = key_events
        if target_episode_number is not None:
            break
    if target_episode_number is None and episodes:
        episodes[0]["key_events"] = [*list(episodes[0].get("key_events") or []), note]
    data["episodes"] = episodes
    return EpisodeOutlinePackage(**data)


def _fallback_episode_outline_patch(feedback: str) -> EpisodeOutlinePatch:
    episode_numbers = _extract_episode_numbers(feedback) or [1]
    note = f"人工修改意见：{feedback}"
    return EpisodeOutlinePatch(
        revision_notes=note,
        episodes=[
            EpisodeOutlineItemPatch(
                episode_number=episode_number,
                key_events=[note],
            )
            for episode_number in episode_numbers
        ],
    )


def _apply_episode_outline_patch(
    current: EpisodeOutlinePackage,
    patch: EpisodeOutlinePatch,
) -> EpisodeOutlinePackage:
    data = current.model_dump(mode="json")
    episodes = list(data.get("episodes") or [])
    by_number = {item.get("episode_number"): item for item in episodes}
    by_id = {item.get("episode_id"): item for item in episodes if item.get("episode_id")}

    for item in patch.episodes:
        target = None
        if item.episode_id:
            target = by_id.get(item.episode_id)
        if target is None:
            target = by_number.get(item.episode_number)
        if target is None:
            continue

        patch_data = item.model_dump(mode="json", exclude_none=True)
        for key, value in patch_data.items():
            if key in {"episode_id", "episode_number"}:
                continue
            if key in {"key_events", "emotional_beats", "characters_and_relationship_changes"}:
                if _is_append_only_human_note(value):
                    target[key] = [*list(target.get(key) or []), *value]
                else:
                    target[key] = value
            else:
                target[key] = value

    data["episodes"] = episodes
    return EpisodeOutlinePackage(**data)


def _extract_episode_number(feedback: str) -> int | None:
    match = re.search(r"第\s*(\d+)\s*集", feedback)
    if match:
        return int(match.group(1))
    match = re.search(r"episode\s*(\d+)", feedback, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extract_episode_numbers(feedback: str) -> list[int]:
    numbers: list[int] = []
    for pattern in [
        r"第\s*(\d+)\s*集",
        r"episode\s*(\d+)",
        r"EP\s*(\d+)",
    ]:
        for match in re.finditer(pattern, feedback, flags=re.IGNORECASE):
            number = int(match.group(1))
            if number not in numbers:
                numbers.append(number)
    return numbers


def _write_model_to_state(
    state: dict[str, Any],
    point: str,
    revised: Any,
    ref: ArtifactRef,
) -> None:
    if point == BRIEF_CONFIRMATION_POINT:
        state["creative_brief"] = revised
        validation = validate_brief(revised)
        state["brief_validation"] = validation
        state["brief_gate_result"] = evaluate_brief_gate(validation)
        validation_ref = ArtifactStore().save(
            job_id=state["job_id"],
            artifact_type=ArtifactType.BRIEF_VALIDATION,
            content=validation,
            summary="人工修订后的创作简报完整性校验结果。",
            created_by=NodeId.HUMAN_BRIEF_CONFIRM,
            parent_ref=ref,
        )
        state.setdefault("artifact_refs", {})["brief_validation"] = validation_ref
    elif point == STYLE_CONFIRMATION_POINT:
        state["style_guide"] = revised
        state["style_guide_summary"] = render_style_guide_context(revised)
    elif point == EPISODE_OUTLINE_CONFIRMATION_POINT:
        state["episode_outline_package"] = revised


def _validate_episode_outline_against_brief(
    outline: EpisodeOutlinePackage,
    state: dict[str, Any],
) -> None:
    brief = state.get("creative_brief")
    if isinstance(brief, dict):
        brief = CreativeBrief(**brief)
    if isinstance(brief, CreativeBrief) and brief.episode_count:
        if len(outline.episodes) != brief.episode_count:
            raise ValueError(
                "Episode outline episode count does not match creative brief: "
                f"{len(outline.episodes)} != {brief.episode_count}"
            )
    episode_numbers = [episode.episode_number for episode in outline.episodes]
    if len(episode_numbers) != len(set(episode_numbers)):
        raise ValueError("Episode outline contains duplicated episode_number values.")


def _invalidate_downstream(state: dict[str, Any], point: str) -> None:
    for key in DOWNSTREAM_STATE_KEYS[point]:
        state.pop(key, None)
    refs = dict(state.get("artifact_refs", {}))
    for key in DOWNSTREAM_ARTIFACT_KEYS[point]:
        refs.pop(key, None)
    state["artifact_refs"] = refs
    invalid_nodes = DOWNSTREAM_COMPLETED_NODES[point]
    state["completed_nodes"] = [
        node for node in state.get("completed_nodes", []) if node not in invalid_nodes
    ]
    if state.get("last_completed_node") in invalid_nodes:
        state["last_completed_node"] = None


def _clear_pause_flags(state: dict[str, Any]) -> None:
    state["human_confirmation_required"] = False
    state["human_confirmation_point"] = None
    state["editable_artifact_refs"] = {}
    state["resume_target_node"] = None
    state["human_questions"] = []
    state["final_message"] = None


def _confirmed_points_without(state: dict[str, Any], point: str) -> list[str]:
    return [item for item in state.get("confirmed_human_points", []) if item != point]


def _summary_for(point: str, revised: Any) -> str:
    if point == BRIEF_CONFIRMATION_POINT:
        return "人工确认修订后的创作简报。"
    if point == STYLE_CONFIRMATION_POINT:
        return getattr(revised, "style_name", "人工确认修订后的创作风格指南。")
    return f"{len(revised.episodes)} 集人工确认修订后的分集大纲。"


def _title_for(point: str) -> str:
    return {
        BRIEF_CONFIRMATION_POINT: "创意简报",
        STYLE_CONFIRMATION_POINT: "创作风格",
        EPISODE_OUTLINE_CONFIRMATION_POINT: "分集大纲",
    }[point]


def _guardrails_for(point: str, state: dict[str, Any]) -> str:
    if point == BRIEF_CONFIRMATION_POINT:
        return "只修改 CreativeBrief 字段；不要生成完整剧本；保持用户原始需求中没有要求删除的硬约束。"
    if point == STYLE_CONFIRMATION_POINT:
        return (
            "只修改 CreativeStyleGuide 字段；所有字段必须是字符串；"
            "不要改变故事剧情、人物关系或分集走向。"
        )
    return "\n\n".join(
        part
        for part in [
            "只修改 EpisodeOutlinePackage；不要改变集数、episode_id 或已锁定人物身份。",
            "普通模式使用局部 patch：只返回需要修改的集数和字段，不要重写未被反馈影响的集。",
            "如反馈没有明确集数，优先做最小范围修改；不要新增或删除分集。",
        ]
        if part
    )


def _episode_outline_revision_context(
    outline: EpisodeOutlinePackage,
    state: dict[str, Any],
    *,
    target_numbers: list[int],
) -> str:
    parts = [
        render_creative_brief_context(state.get("creative_brief")),
        _compact_story_bible_for_outline_revision(state.get("story_bible")),
        _compact_character_bible_for_outline_revision(state.get("character_bible")),
        _compact_style_for_outline_revision(state),
        _compact_episode_outline_for_revision(outline, target_numbers=target_numbers),
    ]
    return "\n\n".join(part for part in parts if part)


def _episode_outline_patch_source(
    outline: EpisodeOutlinePackage,
    target_numbers: list[int],
) -> dict[str, Any]:
    selected_numbers = _episode_numbers_with_neighbors(outline, target_numbers)
    episodes = [
        _episode_patch_source_item(episode, include_full_fields=bool(selected_numbers))
        for episode in outline.episodes
        if not selected_numbers or episode.episode_number in selected_numbers
    ]
    return {
        "outline_package_id": outline.outline_package_id,
        "episodes_for_patch": episodes,
        "note": "只基于这些相关集输出局部 patch；未列出的集默认保持不变。",
    }


def _episode_patch_source_item(episode: Any, *, include_full_fields: bool) -> dict[str, Any]:
    data = episode.model_dump(mode="json") if hasattr(episode, "model_dump") else dict(episode)
    if include_full_fields:
        return data
    return {
        key: data.get(key)
        for key in (
            "episode_id",
            "episode_number",
            "title",
            "episode_positioning",
            "opening_hook",
            "core_conflict",
            "key_events",
            "turning_point_and_climax",
            "ending_and_cliffhanger",
        )
        if data.get(key) not in (None, "", [])
    }


def _compact_story_bible_for_outline_revision(value: Any) -> str:
    data = _to_dict(value)
    if not data:
        return ""
    return "\n".join(
        line
        for line in [
            "【Story Bible 关键约束】",
            _line("故事标题", data.get("title")),
            _line("故事摘要", data.get("summary") or data.get("logline")),
            _line("主题表达", data.get("theme")),
            _line("核心冲突", data.get("core_conflict")),
            _list_line("不可改变事实", data.get("immutable_facts"), limit=8),
            _list_line("世界/叙事规则", data.get("world_rules"), limit=6),
        ]
        if line
    )


def _compact_character_bible_for_outline_revision(value: Any) -> str:
    data = _to_dict(value)
    characters = data.get("characters") or []
    if not characters:
        return ""
    lines = ["【人物系统关键约束】"]
    for item in characters[:8]:
        character = _to_dict(item)
        lines.append(
            "；".join(
                part
                for part in [
                    str(character.get("name") or character.get("character_id") or "未命名角色"),
                    f"角色功能：{character.get('role_type') or character.get('role')}",
                    f"身份：{character.get('identity')}",
                    f"目标：{character.get('external_goal') or character.get('desire')}",
                    f"弧光：{character.get('character_arc')}",
                ]
                if part and not part.endswith("None")
            )
        )
    return "\n".join(lines)


def _compact_style_for_outline_revision(state: dict[str, Any]) -> str:
    summary = str(state.get("style_guide_summary") or "").strip()
    if not summary:
        return ""
    return "【已确认风格边界】\n" + _truncate(summary, 800)


def _compact_episode_outline_for_revision(
    outline: EpisodeOutlinePackage,
    *,
    target_numbers: list[int],
) -> str:
    selected_numbers = _episode_numbers_with_neighbors(outline, target_numbers)
    lines = ["【分集大纲相关片段】"]
    if selected_numbers:
        lines.append(f"本次重点集数及相邻集：{', '.join(str(item) for item in selected_numbers)}")
    else:
        lines.append("用户未明确指定集数，以下为全剧分集的轻量摘要。")
    for episode in outline.episodes:
        if selected_numbers and episode.episode_number not in selected_numbers:
            continue
        lines.append(
            "；".join(
                part
                for part in [
                    f"第{episode.episode_number}集《{episode.title or episode.episode_id}》",
                    f"定位：{episode.episode_positioning}",
                    f"开场：{episode.opening_hook}",
                    f"冲突：{episode.core_conflict}",
                    f"关键事件：{_inline_list(episode.key_events, limit=5)}",
                    f"高潮：{episode.turning_point_and_climax}",
                    f"结尾：{episode.ending_and_cliffhanger}",
                ]
                if part and not part.endswith("None")
            )
        )
    return "\n".join(lines)


def _episode_numbers_with_neighbors(
    outline: EpisodeOutlinePackage,
    target_numbers: list[int],
) -> set[int]:
    available = {episode.episode_number for episode in outline.episodes}
    if not target_numbers:
        return set()
    selected: set[int] = set()
    for number in target_numbers:
        selected.update({number - 1, number, number + 1})
    return {number for number in selected if number in available}


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return {}


def _line(label: str, value: Any) -> str:
    return f"{label}：{value}" if value is not None and value != "" and value != [] else ""


def _list_line(label: str, values: Any, *, limit: int) -> str:
    if not values:
        return ""
    if not isinstance(values, list):
        return _line(label, values)
    return f"{label}：" + "、".join(str(item) for item in values[:limit] if item)


def _inline_list(values: Any, *, limit: int) -> str:
    if not values:
        return ""
    if isinstance(values, list):
        return "、".join(str(item) for item in values[:limit] if item)
    return str(values)


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _is_append_only_human_note(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 1
        and isinstance(value[0], str)
        and value[0].startswith("人工修改意见：")
    )
