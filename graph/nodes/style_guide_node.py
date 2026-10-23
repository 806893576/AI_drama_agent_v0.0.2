"""Creative style guide node."""

from __future__ import annotations

from typing import Any

from domain.brief.schemas import CreativeBrief
from domain.style import CreativeStyleGuide
from schemas.enums import ArtifactType, EventStatus, NodeId, StageId
from services.llm import (
    generate_model_with_fallback,
    json_dumps_for_prompt,
    render_creative_brief_context,
)
from services.storage.artifact_store import ArtifactStore
from services.style import (
    build_creative_style_guide,
    match_style_presets,
    render_style_presets_for_prompt,
)
from state.events import RuntimeEvent


def style_guide_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    user_request = state.get("user_request", "")
    store = ArtifactStore()
    brief = _load_creative_brief_from_state(state, store)
    matched_presets = match_style_presets(brief, user_request=user_request)

    style_guide = generate_model_with_fallback(
        "style.guide",
        {
            "creative_brief": render_creative_brief_context(brief),
            "user_request": user_request,
            "matched_presets": render_style_presets_for_prompt(matched_presets),
        },
        CreativeStyleGuide,
        fallback=lambda: build_creative_style_guide(
            brief,
            user_request=user_request,
            presets=matched_presets,
        ),
        temperature=0.25,
    )

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.STYLE_GUIDE,
        content=style_guide,
        summary=style_guide.style_name,
        created_by=NodeId.STYLE_GUIDE,
        parent_ref=state.get("artifact_refs", {}).get("creative_brief"),
        metadata={"matched_presets": style_guide.matched_presets},
    )
    event = RuntimeEvent(
        event_id=f"{job_id}_style_guide_completed",
        node_id=NodeId.STYLE_GUIDE,
        stage=StageId.BRIEF,
        status=EventStatus.COMPLETED,
        message=f"创作风格指南已生成：{style_guide.style_name}",
        artifact_ids=[ref.artifact_id],
    )
    return {
        "current_stage": StageId.BRIEF,
        "artifact_refs": {"style_guide": ref},
        "style_guide": style_guide,
        "style_guide_summary": render_style_guide_context(style_guide),
        "events": [event],
    }


def render_style_guide_context(style_guide: CreativeStyleGuide | dict | None) -> str:
    if style_guide is None:
        return "未提供风格指南，使用默认短剧电影感风格。"
    guide = (
        style_guide
        if isinstance(style_guide, CreativeStyleGuide)
        else CreativeStyleGuide(**style_guide)
    )
    return "\n".join(
        [
            "【Creative Style Guide / 创作风格指南】",
            f"风格名称：{guide.style_name}",
            f"来源关键词：{guide.source_keywords}",
            f"匹配预设：{guide.matched_presets}",
            f"美术/画风：{guide.visual_style_profile}",
            f"导演风格：{guide.director_style_profile}",
            f"摄影规则：{guide.cinematography_profile}",
            f"光影规则：{guide.lighting_profile}",
            f"色彩系统：{guide.color_palette}",
            f"美术指导：{guide.art_direction_profile}",
            f"渲染媒介：{guide.render_style}",
            f"表演规则：{guide.performance_profile}",
            f"剪辑节奏：{guide.editing_rhythm}",
            f"声音规则：{guide.sound_profile}",
            f"特效规则：{guide.vfx_profile}",
            f"必须执行：{guide.style_do}",
            f"禁止事项：{guide.style_do_not}",
            f"安全说明：{guide.safety_notes}",
        ]
    ).strip()


def style_guide_summary_from_state(state: dict[str, Any]) -> str:
    return state.get("style_guide_summary") or render_style_guide_context(state.get("style_guide"))


def _load_creative_brief_from_state(state: dict, artifact_store: ArtifactStore) -> CreativeBrief:
    brief = state.get("creative_brief")
    if isinstance(brief, CreativeBrief):
        return brief
    if isinstance(brief, dict):
        return CreativeBrief(**brief)

    brief_ref = state.get("artifact_refs", {}).get("creative_brief")
    if brief_ref is not None:
        content = artifact_store.load(brief_ref, job_id=state["job_id"]).content
        return content if isinstance(content, CreativeBrief) else CreativeBrief(**content)

    raw = json_dumps_for_prompt(state)
    raise ValueError(f"CreativeBrief is required before style_guide_node. state={raw[:500]}")
