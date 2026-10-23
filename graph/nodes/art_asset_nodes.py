"""美术 Prompt 与资产登记节点。"""

from __future__ import annotations

import hashlib
import re

from domain.art.image_prompts import (
    ArtAssetPromptLibrary,
    ArtPromptPackage,
    CharacterAssetPrompt,
    PropAssetPrompt,
    SceneAssetPrompt,
    ShotPromptPlan,
)
from domain.assets.asset_registry import (
    AssetRegistry,
    CharacterAsset,
    PromptAsset,
    PropAsset,
    SceneAsset,
    ShotAsset,
)
from domain.story.character_bible import CharacterBible
from domain.style import CreativeStyleGuide
from graph.nodes.style_guide_node import style_guide_summary_from_state
from schemas.enums import ArtifactType, EventStatus, NodeId, StageId
from services.llm import generate_model_with_fallback
from services.storage.artifact_store import ArtifactStore
from services.storage.asset_store import AssetRegistryStore
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


def art_agent_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    package = generate_model_with_fallback(
        "agents.art_agent",
        {
            "style_guide_summary": style_guide_summary_from_state(state),
            "art_input_summary": summarize_art_inputs_for_prompt(state),
        },
        ArtPromptPackage,
        fallback=lambda: build_art_prompt_package(state),
        temperature=0.6,
    )

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.ART_PACKAGE,
        content=package,
        summary=(
            f"角色资产 {len(package.asset_prompts.character_assets)}，"
            f"场景资产 {len(package.asset_prompts.scene_assets)}，"
            f"道具资产 {len(package.asset_prompts.prop_assets)}，"
            f"分镜参考 {len(package.shot_prompt_plan)}。"
        ),
        created_by=NodeId.ART_AGENT,
    )
    return {
        "current_stage": StageId.ART,
        "artifact_refs": {"art_package": ref},
        "art_prompt_package": package,
        "events": [
            _event(
                job_id,
                NodeId.ART_AGENT,
                StageId.ART,
                "美术 Prompt 已生成。",
                [ref.artifact_id],
            )
        ],
    }


def asset_manager_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    artifact_store = ArtifactStore()
    registry_store = AssetRegistryStore()
    registry = build_asset_registry(state)
    registry_store.save(registry)

    ref = artifact_store.save(
        job_id=job_id,
        artifact_type=ArtifactType.ASSET_REGISTRY,
        content=registry,
        summary=(
            f"角色 {len(registry.characters)}，场景 {len(registry.scenes)}，"
            f"镜头 {len(registry.shots)}，Prompt {len(registry.prompts)}。"
        ),
        created_by=NodeId.ASSET_MANAGER,
    )
    return {
        "current_stage": StageId.ASSET,
        "artifact_refs": {"asset_registry": ref},
        "asset_registry_ref": ref,
        "asset_registry": registry,
        "events": [
            _event(
                job_id,
                NodeId.ASSET_MANAGER,
                StageId.ASSET,
                "资产登记已完成。",
                [ref.artifact_id],
            )
        ],
    }


def build_art_prompt_package(state: dict) -> ArtPromptPackage:
    style_profile = _style_profile(state)
    scenes = state.get("scene_breakdowns", [])
    shots = _final_shots_for_art(state)
    scene_assets = _build_scene_asset_prompts(scenes, shots, style_profile)
    prop_assets = _build_prop_asset_prompts(scenes, shots, style_profile)
    character_assets = _build_character_asset_prompts(state, scenes, shots, style_profile)
    shot_prompt_plan = _build_shot_prompt_plan(
        scenes,
        shots,
        character_assets,
        prop_assets,
        style_profile,
    )
    return ArtPromptPackage(
        art_prompt_package_id="art_prompt_package_v001",
        style_profile=style_profile,
        asset_prompts=ArtAssetPromptLibrary(
            character_assets=character_assets,
            scene_assets=scene_assets,
            prop_assets=prop_assets,
        ),
        shot_prompt_plan=shot_prompt_plan,
    )


def summarize_art_inputs_for_prompt(state: dict) -> str:
    """把美术组需要的上下文转成自然语言摘要。"""

    lines = [
        style_guide_summary_from_state(state),
        "",
        "美术组 Agent 任务：生成角色设定图、场景图、关键道具图的文生图 prompt，"
        "并为每个分镜保存角色/场景/道具资产引用和分镜参考图 prompt。",
        f"统一视觉风格：{_style_profile(state)}",
        "核心原则：所有资产和分镜参考图风格必须统一；同一角色同一妆造服装复用同一资产；"
        "同一场景复用同一场景资产；只提取剧情真正需要的关键道具；分镜参考图不改剧情。",
        "",
    ]

    character_bible = state.get("character_bible")
    if isinstance(character_bible, dict):
        character_bible = CharacterBible(**character_bible)
    if character_bible is not None:
        lines.append("可选角色圣经摘要：")
        for character in character_bible.characters:
            lines.append(
                f"- {character.name}：{character.role_type}；"
                f"视觉关键词：{_join_text(character.visual_keywords)}；"
                f"性格/欲望：{character.desire}"
            )
        lines.append("")

    scenes = state.get("scene_breakdowns", [])
    shots = _final_shots_for_art(state)
    shots_by_scene = _shots_by_scene(shots)
    lines.append("场景拆解摘要：")
    for scene in scenes:
        scene_id = _get(scene, "scene_id")
        lines.extend(
            [
                f"- 场景 {scene_id}：{_get(scene, 'interior_exterior')}，"
                f"{_get(scene, 'location')}，时间：{_get(scene, 'time') or '未标注'}。",
                f"  出场人物：{_get(scene, 'characters', '未标注')}",
                f"  关键道具：{_get(scene, 'props', '无')}",
                f"  服装化妆：{_get(scene, 'costume_makeup', '未标注')}",
                f"  场景概要：{_get(scene, 'scene_summary', '')}",
                f"  连续性：{_get(scene, 'continuity', '')}",
                "  该场景关联分镜："
                + _join_text(shot.shot_id for shot in shots_by_scene.get(scene_id, [])),
            ]
        )
    lines.append("")

    lines.append("视听增强版分镜摘要：")
    for shot in shots:
        lines.extend(
            [
                f"- 分镜 {shot.shot_id}，场景 {shot.scene_id}，第 {shot.shot_number} 镜，"
                f"景别：{shot.shot_size}，时长：{shot.duration_seconds} 秒。",
                f"  构图：{shot.composition}",
                f"  镜头内容：{shot.shot_content}",
                f"  机位运动：{shot.camera_position_movement}",
                f"  连续性：{shot.continuity or '未标注'}",
            ]
        )
    return "\n".join(lines).strip()


def _build_character_asset_prompts(
    state: dict,
    scenes: list,
    shots: list,
    style_profile: str,
) -> list[CharacterAssetPrompt]:
    character_names = _character_names_from_sources(state, scenes)
    if not character_names:
        character_names = ["主要角色"]
    shot_ids = [shot.shot_id for shot in shots]
    scene_ids = [_get(scene, "scene_id") for scene in scenes if _get(scene, "scene_id")]
    assets: list[CharacterAssetPrompt] = []
    for name in character_names:
        asset_id = f"char_{_slug(name)}_base"
        assets.append(
            CharacterAssetPrompt(
                asset_id=asset_id,
                character_name=name,
                variant="base",
                used_in_scene_ids=scene_ids,
                used_in_shot_ids=shot_ids,
                prompt=(
                    "生成一张人物的白底角色形象参考图，图片从左到右分别是面部正视特写图、"
                    "角色全身正视图、角色全身侧视图、角色全身后视图，画面比例16:9。"
                    f"统一风格：{style_profile}。人物介绍：姓名“{name}”，基础妆容自然干净，"
                    "基础服装简洁无品牌标识，五官稳定，发型清晰，适合后续根据场景替换服装、发型和妆造。"
                ),
                negative_prompt=_negative_prompt(),
                style_keywords=[style_profile],
                safety_notes=["避免真实明星肖像、真实品牌标识和版权角色相似造型。"],
            )
        )
    return assets


def _build_scene_asset_prompts(
    scenes: list,
    shots: list,
    style_profile: str,
) -> list[SceneAssetPrompt]:
    shots_by_scene = _shots_by_scene(shots)
    assets: list[SceneAssetPrompt] = []
    for scene in scenes:
        scene_id = _get(scene, "scene_id")
        if not scene_id:
            continue
        scene_shots = shots_by_scene.get(scene_id, [])
        assets.append(
            SceneAssetPrompt(
                asset_id=f"scene_{_slug(scene_id)}",
                scene_name=f"{_get(scene, 'location', scene_id)}",
                scene_id=scene_id,
                used_in_shot_ids=[shot.shot_id for shot in scene_shots],
                prompt=(
                    f"{style_profile}。生成场景图：{_get(scene, 'location')}，"
                    f"{_get(scene, 'interior_exterior')}，时间：{_get(scene, 'time') or '未标注'}。"
                    f"场景概要：{_get(scene, 'scene_summary', '')}。"
                    f"布局、陈列、光线和可移动道具需要服务分镜："
                    f"{_join_text(shot.shot_id for shot in scene_shots)}。"
                    "同一场景在不同分镜中可变化视角，但空间结构、道具位置和整体风格保持一致。"
                ),
                negative_prompt=_negative_prompt(),
                style_keywords=[style_profile],
                safety_notes=["不出现真实品牌商标；场景结构保持可复用。"],
            )
        )
    return assets


def _build_prop_asset_prompts(
    scenes: list,
    shots: list,
    style_profile: str,
) -> list[PropAssetPrompt]:
    shots_by_scene = _shots_by_scene(shots)
    props: dict[str, dict[str, set[str]]] = {}
    for scene in scenes:
        scene_id = _get(scene, "scene_id")
        for prop_name in _split_text_items(_get(scene, "props", "")):
            if not _is_key_prop(prop_name):
                continue
            bucket = props.setdefault(prop_name, {"scene_ids": set(), "shot_ids": set()})
            if scene_id:
                bucket["scene_ids"].add(scene_id)
                bucket["shot_ids"].update(shot.shot_id for shot in shots_by_scene.get(scene_id, []))

    assets: list[PropAssetPrompt] = []
    for prop_name, refs in props.items():
        assets.append(
            PropAssetPrompt(
                asset_id=f"prop_{_slug(prop_name)}",
                prop_name=prop_name,
                used_in_scene_ids=sorted(refs["scene_ids"]),
                used_in_shot_ids=sorted(refs["shot_ids"]),
                prompt=(
                    f"{style_profile}。生成关键道具图：{prop_name}。"
                    "道具外貌、材质、尺寸、磨损状态、可读信息和使用痕迹要符合剧情发展；"
                    "如果道具有屏幕、文字或标识，只使用虚构信息，避免真实品牌。"
                ),
                negative_prompt=_negative_prompt(),
                style_keywords=[style_profile],
                safety_notes=["道具文字使用虚构内容；避免真实品牌和侵权标识。"],
            )
        )
    return assets


def _build_shot_prompt_plan(
    scenes: list,
    shots: list,
    character_assets: list[CharacterAssetPrompt],
    prop_assets: list[PropAssetPrompt],
    style_profile: str,
) -> list[ShotPromptPlan]:
    scenes_by_id = {_get(scene, "scene_id"): scene for scene in scenes}
    character_by_name = {asset.character_name: asset.asset_id for asset in character_assets}
    prop_by_name = {asset.prop_name: asset.asset_id for asset in prop_assets}
    plans: list[ShotPromptPlan] = []
    for shot in shots:
        scene = scenes_by_id.get(shot.scene_id)
        scene_asset_id = f"scene_{_slug(shot.scene_id)}"
        characters = _scene_character_names(scene) if scene is not None else []
        props = _split_text_items(_get(scene, "props", "")) if scene is not None else []
        character_asset_ids = [
            character_by_name[name] for name in characters if name in character_by_name
        ]
        prop_asset_ids = [prop_by_name[name] for name in props if name in prop_by_name]
        plans.append(
            ShotPromptPlan(
                shot_id=shot.shot_id,
                scene_id=shot.scene_id,
                scene_asset_id=scene_asset_id,
                character_asset_ids=character_asset_ids,
                prop_asset_ids=prop_asset_ids,
                shot_reference_prompt=(
                    f"{style_profile}。生成单个镜头的分镜参考图。"
                    f"引用场景资产：{scene_asset_id}；"
                    f"引用角色资产：{_join_text(character_asset_ids)}；"
                    f"引用关键道具资产：{_join_text(prop_asset_ids)}。"
                    f"画面构图：{shot.composition}。"
                    f"镜头内容：{shot.shot_content}。"
                    f"机位/运动参考：{shot.camera_position_movement}。"
                    f"连续性要求：{shot.continuity or '承接当前场景整体连续性'}。"
                    "画面只表现当前分镜，不新增剧情，不改变人物行为、服装状态和空间关系。"
                ),
                negative_prompt=_negative_prompt(),
                continuity_notes=shot.continuity,
                video_prompt_source_notes=(
                    "后续视频生成提示词由本地程序从 audiovisual_enhanced_shot_list "
                    "和本美术引用计划中截取字段后组装。"
                ),
            )
        )
    return plans


def _style_profile(state: dict) -> str:
    if state.get("art_style_profile"):
        return str(state["art_style_profile"])
    guide = state.get("style_guide")
    if isinstance(guide, dict):
        guide = CreativeStyleGuide(**guide)
    if isinstance(guide, CreativeStyleGuide):
        parts = [
            guide.visual_style_profile,
            guide.art_direction_profile,
            guide.render_style,
            guide.color_palette,
            guide.lighting_profile,
            guide.style_do,
            guide.style_do_not,
            guide.safety_notes,
        ]
        text = "；".join(part for part in parts if part.strip())
        if text:
            return text
    return "超写实都市短剧电影感，统一冷暖对比光影，商业广告级质感，高清细节，16:9"


def _negative_prompt() -> str:
    return "低清晰度，五官崩坏，多余肢体，文字水印，真实品牌标识，侵权角色相似造型"


def _character_names_from_sources(state: dict, scenes: list) -> list[str]:
    names: list[str] = []
    character_bible = state.get("character_bible")
    if isinstance(character_bible, dict):
        character_bible = CharacterBible(**character_bible)
    if character_bible is not None:
        names.extend(character.name for character in character_bible.characters)
    for scene in scenes:
        names.extend(_scene_character_names(scene))
    return _unique_texts(names)


def _scene_character_names(scene) -> list[str]:
    text = _get(scene, "characters", "")
    names: list[str] = []
    for part in _split_text_items(text):
        if "：" in part:
            _role, value = part.split("：", 1)
            names.extend(_split_text_items(value))
        elif ":" in part:
            _role, value = part.split(":", 1)
            names.extend(_split_text_items(value))
        else:
            names.append(part)
    return [name for name in _unique_texts(names) if name not in {"无", "未标注"}]


def _shots_by_scene(shots: list) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for shot in shots:
        grouped.setdefault(shot.scene_id, []).append(shot)
    return grouped


def _is_key_prop(prop_name: str) -> bool:
    return prop_name not in {"无", "未标注", "按场景需要少量配置"}


def _join_text(values) -> str:
    items = [str(value) for value in values if str(value).strip()]
    return "、".join(items) if items else "无"


def _unique_texts(values) -> list[str]:
    seen = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _slug(value: str) -> str:
    text = str(value).strip().lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    if ascii_text:
        return ascii_text[:48]
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"id_{digest}"


def _final_shots_for_art(state: dict) -> list:
    return (
        state.get("audiovisual_enhanced_shot_list")
        or state.get("performance_direction")
        or state.get("shot_designs", [])
    )


def build_asset_registry(state: dict) -> AssetRegistry:
    job_id = state.get("job_id", "job_unknown")
    registry = AssetRegistry(registry_id=f"{job_id}_asset_registry", job_id=job_id)

    character_bible = state.get("character_bible")
    if isinstance(character_bible, dict):
        character_bible = CharacterBible(**character_bible)
    if character_bible is not None:
        for character in character_bible.characters:
            registry.upsert_character(
                CharacterAsset(
                    asset_id=character.character_id,
                    name=character.name,
                    description=character.desire,
                    role_type=character.role_type,
                    voice_style=character.voice_style,
                    visual_keywords=character.visual_keywords,
                    tags=["character", character.role_type],
                )
            )

    for scene in state.get("scene_breakdowns", []):
        registry.upsert_scene(
            SceneAsset(
                asset_id=scene.scene_id,
                name=scene.scene_id,
                episode_id=scene.episode_id,
                location_id=scene.location,
                time_of_day=scene.time,
                character_ids=_scene_character_ids(scene),
                prop_ids=_split_text_items(scene.props),
                tags=["scene", scene.interior_exterior],
                metadata={
                    "scene_number": scene.scene_number,
                    "costume_makeup": scene.costume_makeup,
                    "scene_summary": scene.scene_summary,
                    "dramatic_function": scene.dramatic_function,
                    "continuity": scene.continuity,
                },
            )
        )
        for prop_id in _split_text_items(scene.props):
            registry.upsert_prop(
                PropAsset(
                    asset_id=prop_id,
                    name=prop_id,
                    first_appearance_scene_id=scene.scene_id,
                    continuity_notes=["后续镜头引用该道具时保持名称和外观一致。"],
                    tags=["prop"],
                )
            )

    for shot in _final_shots_for_art(state):
        registry.upsert_shot(
            ShotAsset(
                asset_id=shot.shot_id,
                scene_id=shot.scene_id,
                shot_order=shot.shot_number,
                tags=["shot"],
                metadata={
                    "shot_size": shot.shot_size,
                    "composition": shot.composition,
                    "shot_content": shot.shot_content,
                    "camera_position_movement": shot.camera_position_movement,
                    "duration_seconds": shot.duration_seconds,
                    "continuity": shot.continuity,
                },
            )
        )

    art_package = state.get("art_prompt_package")
    for prompt_asset in _prompt_assets_from_art_package(art_package):
        registry.upsert_prompt(prompt_asset)

    return registry


def _prompt_assets_from_art_package(package) -> list[PromptAsset]:
    if package is None:
        return []
    assets: list[PromptAsset] = []
    for item in package.asset_prompts.character_assets:
        assets.append(
            PromptAsset(
                asset_id=item.asset_id,
                prompt=item.prompt,
                negative_prompt=item.negative_prompt,
                intended_use="角色设定图",
                character_ids=[item.asset_id],
                safety_notes=item.safety_notes,
                tags=["prompt", "character"],
            )
        )
    for item in package.asset_prompts.scene_assets:
        assets.append(
            PromptAsset(
                asset_id=item.asset_id,
                prompt=item.prompt,
                negative_prompt=item.negative_prompt,
                intended_use="场景图",
                scene_id=item.scene_id,
                safety_notes=item.safety_notes,
                tags=["prompt", "scene"],
            )
        )
    for item in package.asset_prompts.prop_assets:
        assets.append(
            PromptAsset(
                asset_id=item.asset_id,
                prompt=item.prompt,
                negative_prompt=item.negative_prompt,
                intended_use="关键道具图",
                prop_ids=[item.asset_id],
                safety_notes=item.safety_notes,
                tags=["prompt", "prop"],
            )
        )
    for item in package.shot_prompt_plan:
        assets.append(
            PromptAsset(
                asset_id=f"shot_ref_{item.shot_id}",
                prompt=item.shot_reference_prompt,
                negative_prompt=item.negative_prompt,
                intended_use="分镜参考图",
                character_ids=item.character_asset_ids,
                scene_id=item.scene_id,
                prop_ids=item.prop_asset_ids,
                shot_id=item.shot_id,
                safety_notes=[item.continuity_notes] if item.continuity_notes else [],
                tags=["prompt", "shot_reference"],
            )
        )
    return assets


def _get(value, key: str, default=None):
    if hasattr(value, key):
        return getattr(value, key)
    if isinstance(value, dict):
        return value.get(key, default)
    return default


def _scene_character_ids(scene) -> list[str]:
    characters = scene.characters if hasattr(scene, "characters") else scene.get("characters", {})
    if hasattr(characters, "model_dump"):
        characters = characters.model_dump(mode="json")
    if isinstance(characters, dict):
        return [
            *characters.get("leads", []),
            *characters.get("supporting", []),
            *characters.get("extras", []),
        ]
    if isinstance(characters, list):
        return characters
    return _split_text_items(characters)


def _split_text_items(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    separators = ["；", ";", "\n", "、", "，", ","]
    for separator in separators[1:]:
        text = text.replace(separator, separators[0])
    return [item.strip() for item in text.split(separators[0]) if item.strip()]
