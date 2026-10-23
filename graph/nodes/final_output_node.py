"""最终输出节点。

负责汇总创作简报、剧本包、导演方案、视听方案、美术 Prompt、资产清单和审核报告，
生成最终交付包 Artifact。
"""

from __future__ import annotations

from schemas.enums import ArtifactType, EventStatus, NodeId, StageId
from services.storage.artifact_store import ArtifactStore
from state.artifact_refs import get_artifact_ref_id
from state.events import RuntimeEvent


def final_output_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()

    artifact_refs = state.get("artifact_refs", {})
    generation_sections = build_final_generation_sections(state)
    final_package = {
        "package_id": "final_package_v001",
        "schema_version": "1.0",
        "job_id": job_id,
        "source_artifact_ids": {
            key: get_artifact_ref_id(artifact_refs[key])
            for key in ("art_package", "audiovisual_enhanced_shot_list")
            if key in artifact_refs
        },
        "art_package": generation_sections["art_package"],
        "audiovisual_enhanced_shot_list": generation_sections[
            "audiovisual_enhanced_shot_list"
        ],
        "summary": "AI 短剧制作方案生成智能体最终交付包。",
        "artifact_refs": {
            key: ref.model_dump(mode="json") if hasattr(ref, "model_dump") else ref
            for key, ref in artifact_refs.items()
        },
        "acceptance": state.get("final_acceptance_report", {}),
        "sections": {
            "creative_brief": "创作简报",
            "style_guide": "创作风格指南 / 美术风格 / 导演风格 / 视听风格",
            "writer_package": "Story Bible / 人物 / 大纲 / 剧本 / 润色",
            "director_package": "场景拆解 / 分镜 / 表演调度",
            "audiovisual_package": "视听增强版最终分镜",
            "art_package": "角色 / 场景 / 分镜视觉 Prompt",
            "asset_registry": "角色 / 场景 / 道具 / 镜头 / Prompt 资产登记",
            "reviews": "剧本审核 / 质量评分 / 安全审核 / 一致性审核 / 最终验收",
        },
    }

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.FINAL_PACKAGE,
        content=final_package,
        summary=final_package["summary"],
        created_by=NodeId.FINAL_OUTPUT,
    )

    event = RuntimeEvent(
        event_id=f"{job_id}_final_output_completed",
        node_id=NodeId.FINAL_OUTPUT,
        stage=StageId.FINAL,
        status=EventStatus.COMPLETED,
        message="最终交付包已生成。",
        artifact_ids=[ref.artifact_id],
    )

    return {
        "current_stage": StageId.FINAL,
        "artifact_refs": {"final_package": ref},
        "final_package": final_package,
        "final_output_ready": True,
        "final_message": "AI 短剧制作方案已完成，最终交付包已生成。",
        "events": [event],
    }


def build_final_generation_sections(state: dict) -> dict:
    """将美术资产与最终分镜确定性地组装成下游生成清单。"""

    package = state.get("art_prompt_package")
    asset_prompts = _get(package, "asset_prompts", {})
    character_assets = _as_list(_get(asset_prompts, "character_assets", []))
    scene_assets = _as_list(_get(asset_prompts, "scene_assets", []))
    prop_assets = _as_list(_get(asset_prompts, "prop_assets", []))
    shot_plans = _as_list(_get(package, "shot_prompt_plan", []))

    characters_by_id = {
        str(_get(asset, "asset_id")): asset
        for asset in character_assets
        if _get(asset, "asset_id")
    }
    scenes_by_id = {
        str(_get(asset, "scene_id")): asset
        for asset in scene_assets
        if _get(asset, "scene_id")
    }
    scenes_by_asset_id = {
        str(_get(asset, "asset_id")): asset
        for asset in scene_assets
        if _get(asset, "asset_id")
    }
    props_by_id = {
        str(_get(asset, "asset_id")): asset
        for asset in prop_assets
        if _get(asset, "asset_id")
    }
    plans_by_shot_id = {
        str(_get(plan, "shot_id")): plan
        for plan in shot_plans
        if _get(plan, "shot_id")
    }

    compact_art_package = {
        "style_profile": str(_get(package, "style_profile", "") or ""),
        "character_assets": [
            {
                "character_name": str(_get(asset, "character_name", "") or ""),
                "variant": str(_get(asset, "variant", "") or ""),
                "prompt": str(_get(asset, "prompt", "") or ""),
            }
            for asset in character_assets
        ],
        "scene_assets": [
            {
                "scene": [
                    _scene_label(
                        _get(asset, "scene_id", ""),
                        _get(asset, "scene_name", ""),
                    )
                ],
                "prompt": str(_get(asset, "prompt", "") or ""),
            }
            for asset in scene_assets
        ],
        "prop_assets": [
            {
                "prop_name": str(_get(asset, "prop_name", "") or ""),
                "used_in_scene_ids": [
                    str(scene_id)
                    for scene_id in _as_list(_get(asset, "used_in_scene_ids", []))
                ],
                "prompt": str(_get(asset, "prompt", "") or ""),
            }
            for asset in prop_assets
        ],
    }

    compact_shots: list[dict] = []
    for shot in _as_list(state.get("audiovisual_enhanced_shot_list", [])):
        shot_id = str(_get(shot, "shot_id", "") or "")
        scene_id = str(_get(shot, "scene_id", "") or "")
        plan = plans_by_shot_id.get(shot_id)
        scene_asset = scenes_by_id.get(scene_id)
        if scene_asset is None and plan is not None:
            scene_asset = scenes_by_asset_id.get(str(_get(plan, "scene_asset_id", "") or ""))

        character_ids = _as_list(_get(plan, "character_asset_ids", []))
        if not character_ids:
            character_ids = [
                asset_id
                for asset_id, asset in characters_by_id.items()
                if shot_id in _as_list(_get(asset, "used_in_shot_ids", []))
            ]
        prop_ids = _as_list(_get(plan, "prop_asset_ids", []))
        if not prop_ids:
            prop_ids = [
                asset_id
                for asset_id, asset in props_by_id.items()
                if shot_id in _as_list(_get(asset, "used_in_shot_ids", []))
            ]

        characters = _unique_strings(
            _character_label(characters_by_id.get(str(asset_id)))
            for asset_id in character_ids
        )
        props = _unique_strings(
            _get(props_by_id.get(str(asset_id)), "prop_name", "")
            for asset_id in prop_ids
        )

        compact_shots.append(
            {
                "shot_id": shot_id,
                "scene": [
                    _scene_label(
                        scene_id,
                        _get(scene_asset, "scene_name", ""),
                    )
                ],
                "shot_number": _get(shot, "shot_number"),
                "characters": characters,
                "props": props,
                "shot_content": str(_get(shot, "shot_content", "") or ""),
                "continuity": _get(shot, "continuity"),
            }
        )

    return {
        "art_package": compact_art_package,
        "audiovisual_enhanced_shot_list": compact_shots,
    }


def _scene_label(scene_id, scene_name) -> str:
    parts = [str(value).strip() for value in (scene_id, scene_name) if str(value).strip()]
    return "_".join(parts)


def _character_label(asset) -> str:
    if asset is None:
        return ""
    name = str(_get(asset, "character_name", "") or "").strip()
    variant = str(_get(asset, "variant", "") or "").strip()
    return "_".join(part for part in (name, variant) if part)


def _unique_strings(values) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list | tuple):
        return list(value)
    return [value]


def _get(value, key: str, default=None):
    if value is None:
        return default
    if hasattr(value, key):
        return getattr(value, key)
    if isinstance(value, dict):
        return value.get(key, default)
    return default
