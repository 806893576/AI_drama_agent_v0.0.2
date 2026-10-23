"""导演子图节点。

导演阶段拆成三个独立 LLM 调用：
场景拆解读取自然语言化剧本，分镜设计读取剧本摘要和场景拆解摘要，
表演调度读取分镜摘要和场景拆解摘要。
"""

from __future__ import annotations

from typing import Any

from domain.directing.scene_breakdown import SceneBreakdown
from domain.directing.shot_design import ShotDesign
from domain.story.episode_script import EpisodeScript
from graph.nodes.style_guide_node import style_guide_summary_from_state
from schemas.enums import ArtifactType, EventStatus, NodeId, StageId
from services.llm import generate_model_with_fallback
from services.storage.artifact_store import ArtifactStore
from state.artifact_refs import get_artifact_ref_id
from state.events import RuntimeEvent


def _event(job_id: str, node_id: NodeId, message: str, artifact_ids: list[str]) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=f"{job_id}_{node_id.value.replace('.', '_')}_completed",
        node_id=node_id,
        stage=StageId.DIRECTOR,
        status=EventStatus.COMPLETED,
        message=message,
        artifact_ids=artifact_ids,
    )


def scene_breakdown_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    scripts = [_ensure_episode_script(item) for item in state.get("episode_scripts", [])]
    episode_script_summary = summarize_episode_scripts_for_director(scripts)

    breakdowns = generate_model_with_fallback(
        "director.scene_breakdown",
        {
            "episode_script_summary": episode_script_summary,
            "style_guide_summary": style_guide_summary_from_state(state),
        },
        list[SceneBreakdown],
        fallback=lambda: build_scene_breakdowns(scripts),
        temperature=0.4,
    )

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.SCENE_BREAKDOWN,
        content=breakdowns,
        summary=f"{len(breakdowns)} 个可拍摄场景。",
        created_by=NodeId.DIRECTOR_SCENE_BREAKDOWN,
        parent_ref=state.get("artifact_refs", {}).get("episode_script"),
    )
    return {
        "current_stage": StageId.DIRECTOR,
        "artifact_refs": {"scene_breakdown": ref},
        "scene_breakdowns": breakdowns,
        "events": [
            _event(
                job_id,
                NodeId.DIRECTOR_SCENE_BREAKDOWN,
                "场景拆解已拆分保存。",
                [ref.artifact_id],
            )
        ],
    }


def shot_design_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    scripts = [_ensure_episode_script(item) for item in state.get("episode_scripts", [])]
    breakdowns = [_ensure_scene(item) for item in state.get("scene_breakdowns", [])]

    shots = generate_model_with_fallback(
        "director.shot_design",
        {
            "episode_script_summary": summarize_episode_scripts_for_director(scripts),
            "scene_breakdown_summary": summarize_scene_breakdowns_for_director(breakdowns),
            "style_guide_summary": style_guide_summary_from_state(state),
        },
        list[ShotDesign],
        fallback=lambda: build_shot_designs(breakdowns),
        temperature=0.45,
    )

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.SHOT_LIST,
        content=shots,
        summary=f"{len(shots)} 个分镜镜头。",
        created_by=NodeId.DIRECTOR_SHOT_DESIGN,
        parent_ref=state.get("artifact_refs", {}).get("scene_breakdown"),
    )
    return {
        "current_stage": StageId.DIRECTOR,
        "artifact_refs": {"shot_list": ref},
        "shot_designs": shots,
        "events": [
            _event(
                job_id,
                NodeId.DIRECTOR_SHOT_DESIGN,
                "分镜设计已拆分保存。",
                [ref.artifact_id],
            )
        ],
    }


def performance_direction_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    breakdowns = [_ensure_scene(item) for item in state.get("scene_breakdowns", [])]
    shots = [_ensure_shot(item) for item in state.get("shot_designs", [])]

    performance_shots = generate_model_with_fallback(
        "director.performance",
        {
            "scene_breakdown_summary": summarize_scene_breakdowns_for_director(breakdowns),
            "shot_design_summary": summarize_shot_designs_for_director(shots),
            "style_guide_summary": style_guide_summary_from_state(state),
        },
        list[ShotDesign],
        fallback=lambda: build_performance_direction(shots, breakdowns),
        temperature=0.45,
    )

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.PERFORMANCE_DIRECTION,
        content=performance_shots,
        summary=f"{len(performance_shots)} 个表演增强版镜头。",
        created_by=NodeId.DIRECTOR_PERFORMANCE,
        parent_ref=state.get("artifact_refs", {}).get("shot_list"),
    )
    return {
        "current_stage": StageId.DIRECTOR,
        "artifact_refs": {"performance_direction": ref},
        "performance_direction": performance_shots,
        "events": [
            _event(
                job_id,
                NodeId.DIRECTOR_PERFORMANCE,
                "表演调度已拆分保存。",
                [ref.artifact_id],
            )
        ],
    }


def build_director_package_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    refs = state.get("artifact_refs", {})

    package = {
        "package_id": "director_package_v001",
        "artifact_ids": {
            key: get_artifact_ref_id(ref)
            for key, ref in refs.items()
            if key in {"style_guide", "scene_breakdown", "shot_list", "performance_direction"}
        },
        "scene_ids": [item.scene_id for item in state.get("scene_breakdowns", [])],
        "shot_ids": [item.shot_id for item in state.get("shot_designs", [])],
        "performance_shot_ids": [
            item.shot_id for item in state.get("performance_direction", [])
        ],
    }
    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.DIRECTOR_PACKAGE,
        content=package,
        summary="包含导演阶段关键产物引用、场景/镜头索引和表演增强版镜头索引。",
        created_by=NodeId.DIRECTOR_PACKAGE,
    )
    return {
        "current_stage": StageId.DIRECTOR,
        "artifact_refs": {"director_package": ref},
        "director_package": package,
        "events": [_event(job_id, NodeId.DIRECTOR_PACKAGE, "导演方案已汇总。", [ref.artifact_id])],
    }


def build_scene_breakdowns(scripts: list[EpisodeScript]) -> list[SceneBreakdown]:
    breakdowns: list[SceneBreakdown] = []
    for script in scripts:
        character_names = [character.name for character in script.episode.appearing_characters]
        for scene in script.scenes:
            scene_id = _scene_ref(script, scene)
            breakdowns.append(
                SceneBreakdown(
                    scene_id=scene_id,
                    episode_id=_episode_ref(script),
                    scene_number=scene.scene_number,
                    interior_exterior=scene.interior_exterior,
                    time=_scene_time(scene),
                    location=scene.location,
                    characters=_scene_characters_text(character_names),
                    props=_join_text(_extract_key_props(scene.script_text)),
                    costume_makeup=(
                        "服装按人物当前身份和上一场连续性保持状态；"
                        "妆面保持基础状态，并延续上一场伤口、灰尘、疲惫等细节。"
                    ),
                    scene_summary=_first_sentence(scene.script_text, limit=160),
                    key_actions=_join_text(_extract_key_actions(scene.script_text)),
                    dramatic_function=script.episode.core_function,
                    continuity=_scene_continuity_text(scene, character_names),
                )
            )
    return breakdowns


def build_shot_designs(breakdowns: list[SceneBreakdown]) -> list[ShotDesign]:
    shots: list[ShotDesign] = []
    for scene in breakdowns:
        shots.append(
            ShotDesign(
                shot_id=f"{scene.scene_id}_shot_01",
                scene_id=scene.scene_id,
                shot_number=1,
                shot_size="中景",
                composition="主要人物占画面中心偏前景，保留对手或空间压力方向。",
                shot_content=(
                    f"{scene.scene_summary} 画面先交代{scene.location}和人物关系，"
                    "对白保留剧本核心冲突信息。"
                ),
                camera_position_movement="平视机位，缓慢推进",
                duration_seconds=6.0,
                continuity=scene.continuity,
            )
        )
        shots.append(
            ShotDesign(
                shot_id=f"{scene.scene_id}_shot_02",
                scene_id=scene.scene_id,
                shot_number=2,
                shot_size="近景/特写",
                composition="压缩背景，突出主角眼神、手部动作或关键道具。",
                shot_content=(
                    "承接上一镜头的冲突焦点，切入人物反应和关键对白，"
                    f"强调戏剧功能：{scene.dramatic_function}"
                ),
                camera_position_movement="固定机位或轻微推近",
                duration_seconds=5.0,
                continuity="紧接上一分镜最后一帧的情绪和站位。",
            )
        )
    return shots


def build_performance_direction(
    shots: list[ShotDesign],
    breakdowns: list[SceneBreakdown],
) -> list[ShotDesign]:
    scenes = {scene.scene_id: scene for scene in breakdowns}
    performance_shots: list[ShotDesign] = []
    for shot in shots:
        scene = scenes.get(shot.scene_id)
        character_text = scene.characters if scene else "出场人物"
        performance_shots.append(
            shot.model_copy(
                update={
                    "shot_content": (
                        f"{shot.shot_content} 表演调度：{character_text}的站位保持清晰，"
                        "主控人物占画面前景或视觉优势位，被动人物略后或被桌椅/门框压住。"
                        "动作细节需要有起承转合：抬眼、停顿、靠近或后退都要接住上一镜头。"
                        "表情从克制到变化，特写中细化眼神、眉头、呼吸和嘴角；"
                        "台词节奏在关键信息前停半拍，压低或加快必须服务冲突升级。"
                        "如果紧接上一镜头，手中道具、身体朝向、人物距离和情绪强度不能跳变。"
                    )
                }
            )
        )
    return performance_shots


def summarize_episode_scripts_for_director(scripts: list[EpisodeScript]) -> str:
    """把 episode_script 转成导演节点使用的自然语言摘要。"""

    lines: list[str] = []
    for script in scripts:
        metadata = script.project_metadata
        episode = script.episode
        lines.extend(
            [
                f"剧名：{metadata.title}",
                f"类型：{metadata.genre}",
                f"总集数：{metadata.total_episodes}",
                f"单集：第 {episode.episode_number} 集《{episode.episode_title or '未命名'}》",
                f"核心功能：{episode.core_function}",
                "本集出场人物："
                + _join_text(character.name for character in episode.appearing_characters),
                f"结尾钩子：{episode.ending_hook or '未标注'}",
                "场景正文：",
            ]
        )
        for scene in script.scenes:
            time_text = _scene_time(scene) or "未标注"
            lines.extend(
                [
                    (
                        f"- 场次 {scene.scene_number}（{_scene_ref(script, scene)}）："
                        f"{scene.interior_exterior}，{scene.location}，{time_text}。"
                    ),
                    f"  剧情正文：{_normalize_text(scene.script_text)}",
                ]
            )
        lines.append("")
    return "\n".join(lines).strip()


def summarize_scene_breakdowns_for_director(breakdowns: list[SceneBreakdown]) -> str:
    """把场景拆解结果转成给下游导演节点使用的自然语言摘要。"""

    lines: list[str] = []
    for scene in breakdowns:
        lines.extend(
            [
                f"- 场景 {scene.scene_id}：第 {scene.scene_number} 场，{scene.interior_exterior}，"
                f"{scene.location}，时间：{scene.time or '未标注'}。",
                f"  出场人物：{scene.characters or '无'}。",
                f"  关键道具：{scene.props or '无'}。",
                f"  服装化妆：{scene.costume_makeup or '无'}。",
                f"  场景概要：{scene.scene_summary}",
                f"  关键动作：{scene.key_actions or '无'}。",
                f"  戏剧功能：{scene.dramatic_function}",
                f"  连续性描述：{scene.continuity or '无'}。",
            ]
        )
    return "\n".join(lines).strip()


def summarize_shot_designs_for_director(shots: list[ShotDesign]) -> str:
    """把分镜设计结果转成表演调度节点使用的自然语言摘要。"""

    lines: list[str] = []
    for shot in shots:
        lines.extend(
            [
                f"- 镜头 {shot.shot_id}：属于场景 {shot.scene_id}，第 {shot.shot_number} 镜。",
                f"  景别：{shot.shot_size}。",
                f"  构图：{shot.composition}",
                f"  镜头内容：{shot.shot_content}",
                f"  机位/运动：{shot.camera_position_movement}",
                f"  时长：{shot.duration_seconds} 秒。",
                f"  连续性：{shot.continuity or '未标注'}。",
            ]
        )
    return "\n".join(lines).strip()


def _ensure_model(value: Any, model_type: type) -> Any:
    if isinstance(value, model_type):
        return value
    if isinstance(value, dict):
        return model_type(**value)
    raise TypeError(f"Expected {model_type.__name__}, got {type(value).__name__}")


def _ensure_scene(value: SceneBreakdown | dict) -> SceneBreakdown:
    return value if isinstance(value, SceneBreakdown) else SceneBreakdown(**value)


def _ensure_shot(value: ShotDesign | dict) -> ShotDesign:
    return value if isinstance(value, ShotDesign) else ShotDesign(**value)


def _ensure_episode_script(value: EpisodeScript | dict) -> EpisodeScript:
    return value if isinstance(value, EpisodeScript) else EpisodeScript(**value)


def _episode_ref(script: EpisodeScript) -> str:
    return f"EP_{script.episode.episode_number:03d}"


def _scene_ref(script: EpisodeScript, scene) -> str:
    return f"{_episode_ref(script)}_SC_{scene.scene_number:03d}"


def _scene_time(scene) -> str | None:
    if scene.time and scene.continuity:
        return f"{scene.time}，{scene.continuity}"
    return scene.time or scene.continuity


def _scene_characters_text(character_names: list[str]) -> str:
    if not character_names:
        return "主角：未标注；配角：未标注；群演：无"
    lead = character_names[0]
    supporting = "、".join(character_names[1:]) if len(character_names) > 1 else "无"
    return f"主角：{lead}；配角：{supporting}；群演：按场景需要少量配置"


def _extract_key_props(script_text: str) -> list[str]:
    props = []
    for keyword in (
        "手机",
        "短信",
        "文件",
        "名片",
        "行李箱",
        "海报",
        "合同",
        "钥匙",
        "优惠券",
        "会说话的优惠券",
        "收银机",
        "魔法收银机",
        "账本",
        "旧游戏机",
        "游戏机",
        "像素录像",
        "录像",
    ):
        if keyword in script_text:
            props.append(keyword)
    return props


def _extract_key_actions(script_text: str) -> list[str]:
    actions = []
    for keyword in ("走进", "抬头", "看向", "拿起", "放下", "转身", "震动", "愣住"):
        if keyword in script_text:
            actions.append(keyword)
    return actions or [_first_sentence(script_text, limit=80)]


def _scene_continuity_text(scene, character_names: list[str]) -> str:
    notes = []
    if scene.continuity:
        notes.append(f"本场时间与空间连续性：{scene.continuity}。")
    for name in character_names[:3]:
        notes.append(f"{name}的服装、妆面、手中道具和情绪状态必须承接上一场。")
    notes.append("场景内关键道具位置和人物站位在后续镜头中保持一致。")
    return "；".join(notes)


def _first_sentence(text: str, *, limit: int) -> str:
    normalized = _normalize_text(text)
    for mark in ("。", "！", "？", "\n"):
        if mark in normalized:
            normalized = normalized.split(mark, 1)[0] + mark
            break
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _normalize_text(text: str) -> str:
    return " ".join(str(text).split())


def _join_text(values: Any) -> str:
    items = [str(value) for value in values if str(value).strip()]
    return "、".join(items) if items else "无"
