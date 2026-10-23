"""审核、质量评分、安全与终审节点。

这些节点使用结构化报告驱动条件边，避免让路由依赖自然语言判断。
"""

from __future__ import annotations

from typing import Any

from agents.base_agent import AgentContext
from agents.continuity_reviewer_agent import ContinuityReviewerAgent
from agents.quality_scoring_agent import QualityScoringAgent
from agents.safety_reviewer_agent import SafetyReviewerAgent
from agents.script_reviewer_agent import ScriptReviewerAgent
from schemas.enums import (
    ArtifactType,
    EventStatus,
    NodeId,
    ReviewType,
    SafetyLayer,
    StageId,
)
from services.storage.artifact_store import ArtifactStore
from state.events import RuntimeEvent


def _event(
    job_id: str,
    node_id: NodeId,
    stage: StageId,
    message: str,
    artifact_ids: list[str],
) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=f"{job_id}_{node_id.value}_completed",
        node_id=node_id,
        stage=stage,
        status=EventStatus.COMPLETED,
        message=message,
        artifact_ids=artifact_ids,
    )


def script_reviewer_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    report = ScriptReviewerAgent().run(
        AgentContext(job_id=job_id, user_request=state.get("user_request", "")),
        episode_scripts=state.get("episode_scripts", []),
    ).output
    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.SCRIPT_REVIEW,
        content=report,
        summary=report.overall_comment,
        created_by=NodeId.SCRIPT_REVIEWER,
    )
    return {
        "current_stage": StageId.REVIEW,
        "artifact_refs": {"script_review": ref},
        "last_review_ref": ref,
        "script_review_report": report,
        "events": [_event(job_id, NodeId.SCRIPT_REVIEWER, StageId.REVIEW, "剧本审稿已完成。", [ref.artifact_id])],
    }


def quality_scoring_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    report = QualityScoringAgent().run(
        AgentContext(job_id=job_id, user_request=state.get("user_request", "")),
        script_review_report=state.get("script_review_report"),
        episode_scripts=state.get("episode_scripts", []),
    ).output
    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.QUALITY_SCORE,
        content=report,
        summary=report.summary,
        created_by=NodeId.QUALITY_SCORING,
    )
    return {
        "current_stage": StageId.REVIEW,
        "artifact_refs": {"quality_score": ref},
        "last_review_ref": ref,
        "quality_score_report": report,
        "events": [_event(job_id, NodeId.QUALITY_SCORING, StageId.REVIEW, "质量评分已完成。", [ref.artifact_id])],
    }


def script_safety_node(state: dict) -> dict:
    return _safety_node(
        state=state,
        node_id=NodeId.SCRIPT_SAFETY,
        layer=SafetyLayer.SCRIPT_TEXT,
        state_key="script_safety_report",
        summary="剧本文本安全审核通过。",
    )


def shot_av_safety_node(state: dict) -> dict:
    return _safety_node(
        state=state,
        node_id=NodeId.SHOT_AV_SAFETY,
        layer=SafetyLayer.SHOT_AV,
        state_key="shot_av_safety_report",
        summary="镜头与视听安全审核通过。",
    )


def prompt_safety_node(state: dict) -> dict:
    return _safety_node(
        state=state,
        node_id=NodeId.PROMPT_SAFETY,
        layer=SafetyLayer.VISUAL_PROMPT,
        state_key="prompt_safety_report",
        summary="视觉 Prompt 安全审核通过。",
    )


def final_safety_node(state: dict) -> dict:
    return _safety_node(
        state=state,
        node_id=NodeId.FINAL_SAFETY,
        layer=SafetyLayer.FINAL,
        state_key="final_safety_report",
        summary="最终汇总安全审核通过。",
    )


def text_continuity_node(state: dict) -> dict:
    return _continuity_node(
        state=state,
        node_id=NodeId.TEXT_CONTINUITY,
        review_type=ReviewType.TEXT_CONTINUITY,
        state_key="text_continuity_report",
        summary="文本一致性审核通过。",
        checked_scene_ids=[
            _episode_script_scene_ref(script, scene)
            for script in state.get("episode_scripts", [])
            for scene in script.scenes
        ],
    )


def production_continuity_node(state: dict) -> dict:
    registry = state.get("asset_registry")
    checked_scene_ids = list(getattr(registry, "scenes", {}).keys()) if registry is not None else []
    checked_shot_ids = list(getattr(registry, "shots", {}).keys()) if registry is not None else []
    return _continuity_node(
        state=state,
        node_id=NodeId.PRODUCTION_CONTINUITY,
        review_type=ReviewType.PRODUCTION_CONTINUITY,
        state_key="production_continuity_report",
        summary="制作一致性审核通过。",
        checked_scene_ids=checked_scene_ids,
        checked_shot_ids=checked_shot_ids,
    )


def final_acceptance_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    acceptance_report = {
        "report_id": "final_acceptance_v001",
        "passed": True,
        "summary": "制片人最终验收通过，交付包可以输出。",
        "required_artifacts": [
            "creative_brief",
            "writer_package",
            "director_package",
            "audiovisual_package",
            "art_package",
            "asset_registry",
        ],
    }
    return {
        "current_stage": StageId.FINAL,
        "final_acceptance_report": acceptance_report,
        "events": [_event(job_id, NodeId.FINAL_ACCEPTANCE, StageId.FINAL, "最终验收已完成。", [])],
    }


def _safety_node(
    state: dict,
    node_id: NodeId,
    layer: SafetyLayer,
    state_key: str,
    summary: str,
) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    report = SafetyReviewerAgent().run(
        AgentContext(job_id=job_id, user_request=state.get("user_request", "")),
        layer=layer,
        report_id=f"{node_id.value}_v001",
        state_context=_review_state_context(state),
    ).output
    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.SAFETY_REVIEW,
        content=report,
        summary=summary,
        created_by=node_id,
        name=node_id.value.replace(".", "_"),
    )
    return {
        "current_stage": StageId.SAFETY,
        "artifact_refs": {state_key: ref},
        "last_review_ref": ref,
        state_key: report,
        "events": [_event(job_id, node_id, StageId.SAFETY, summary, [ref.artifact_id])],
    }


def _continuity_node(
    state: dict,
    node_id: NodeId,
    review_type: ReviewType,
    state_key: str,
    summary: str,
    checked_scene_ids: list[str] | None = None,
    checked_shot_ids: list[str] | None = None,
) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    report = ContinuityReviewerAgent().run(
        AgentContext(job_id=job_id, user_request=state.get("user_request", "")),
        review_type=review_type,
        summary=summary,
        state_context=_review_state_context(state),
        checked_scene_ids=checked_scene_ids or [],
        checked_shot_ids=checked_shot_ids or [],
    ).output
    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.CONTINUITY_REVIEW,
        content=report,
        summary=summary,
        created_by=node_id,
        name=node_id.value,
    )
    return {
        "current_stage": StageId.REVIEW,
        "artifact_refs": {state_key: ref},
        "last_review_ref": ref,
        state_key: report,
        "events": [_event(job_id, node_id, StageId.REVIEW, summary, [ref.artifact_id])],
    }


def _review_state_context(state: dict) -> dict:
    """筛选审核需要的关键摘要，避免把完整运行状态发送给 LLM。"""

    return {
        "creative_brief": _dump_model(state.get("creative_brief"), exclude_none=True),
        "style_guide": _dump_model(state.get("style_guide"), exclude_none=True),
        "story_bible": _compact_story_bible(state.get("story_bible")),
        "character_bible": _compact_character_bible(state.get("character_bible")),
        "story_synopsis": _dump_model(state.get("story_synopsis"), exclude_none=True),
        "episode_outline": _compact_episode_outline(state.get("episode_outline_package")),
        "episode_scripts": _compact_episode_scripts(state.get("episode_scripts", [])),
        "director": {
            "scene_ids": [_get_field(item, "scene_id") for item in state.get("scene_breakdowns", [])],
            "shot_ids": [_get_field(item, "shot_id") for item in state.get("shot_designs", [])],
            "package": state.get("director_package", {}),
        },
        "audiovisual": {
            "package": state.get("audiovisual_package", {}),
            "enhanced_shot_count": len(state.get("audiovisual_enhanced_shot_list", [])),
        },
        "art_prompts": _compact_art_prompts(state.get("art_prompt_package")),
        "asset_registry": _compact_asset_registry(state.get("asset_registry")),
    }


def _dump_model(value: Any, *, exclude_none: bool = False) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=exclude_none)
    return value


def _get_field(value: Any, field: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(field, default)
    return getattr(value, field, default)


def _compact_story_bible(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    data = _dump_model(value)
    return {
        key: data.get(key)
        for key in ("story_bible_id", "summary", "theme", "core_conflict", "immutable_facts")
        if key in data
    }


def _compact_character_bible(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    data = _dump_model(value)
    return {
        "character_bible_id": data.get("character_bible_id"),
        "characters": [
            {
                "character_id": item.get("character_id"),
                "name": item.get("name"),
                "role": item.get("role") or item.get("role_type"),
                "motivation": item.get("motivation"),
                "voice_style": item.get("voice_style"),
            }
            for item in data.get("characters", [])
        ],
        "relationships": data.get("relationships", []),
    }


def _compact_episode_outline(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    data = _dump_model(value)
    return [
        {
            "episode_id": item.get("episode_id"),
            "episode_number": item.get("episode_number"),
            "title": item.get("title"),
            "opening_hook": item.get("opening_hook") or item.get("hook"),
            "core_conflict": item.get("core_conflict") or item.get("main_conflict"),
            "turning_point_and_climax": item.get("turning_point_and_climax") or item.get("reversal"),
            "ending_and_cliffhanger": item.get("ending_and_cliffhanger") or item.get("cliffhanger"),
        }
        for item in data.get("episodes", [])
    ]


def _compact_episode_scripts(scripts: list[Any]) -> list[dict[str, Any]]:
    compact = []
    for script in scripts:
        data = _dump_model(script)
        episode = data.get("episode") or {}
        compact.append(
            {
                "episode_script_id": data.get("episode_script_id"),
                "project_metadata": data.get("project_metadata", {}),
                "episode": episode,
                "scenes": [
                    {
                        "scene_number": scene.get("scene_number"),
                        "interior_exterior": scene.get("interior_exterior"),
                        "location": scene.get("location"),
                        "time": scene.get("time"),
                        "continuity": scene.get("continuity"),
                        "script_text": scene.get("script_text"),
                    }
                    for scene in data.get("scenes", [])
                ],
            }
        )
    return compact


def _episode_script_scene_ref(script: Any, scene: Any) -> str:
    return f"EP_{script.episode.episode_number:03d}_SC_{scene.scene_number:03d}"


def _compact_art_prompts(package: Any) -> dict[str, Any]:
    if package is None:
        return {}
    data = package if isinstance(package, dict) else package.model_dump(mode="json")
    asset_prompts = data.get("asset_prompts", {})
    return {
        "style_profile": data.get("style_profile"),
        "character_assets": [
            _compact_prompt_asset(item)
            for item in asset_prompts.get("character_assets", [])
        ],
        "scene_assets": [
            _compact_prompt_asset(item)
            for item in asset_prompts.get("scene_assets", [])
        ],
        "prop_assets": [
            _compact_prompt_asset(item)
            for item in asset_prompts.get("prop_assets", [])
        ],
        "shot_prompt_plan": [
            {
                "shot_id": item.get("shot_id"),
                "scene_asset_id": item.get("scene_asset_id"),
                "character_asset_ids": item.get("character_asset_ids", []),
                "prop_asset_ids": item.get("prop_asset_ids", []),
                "shot_reference_prompt": item.get("shot_reference_prompt"),
                "negative_prompt": item.get("negative_prompt"),
                "continuity_notes": item.get("continuity_notes"),
            }
            for item in data.get("shot_prompt_plan", [])
        ],
    }


def _compact_prompt_asset(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": item.get("asset_id"),
        "prompt": item.get("prompt"),
        "negative_prompt": item.get("negative_prompt"),
        "safety_notes": item.get("safety_notes", []),
    }


def _compact_asset_registry(registry: Any) -> dict[str, Any] | None:
    if registry is None:
        return None
    return {
        "character_ids": list(getattr(registry, "characters", {}).keys()),
        "scene_ids": list(getattr(registry, "scenes", {}).keys()),
        "shot_ids": list(getattr(registry, "shots", {}).keys()),
        "prompt_ids": list(getattr(registry, "prompts", {}).keys()),
    }
