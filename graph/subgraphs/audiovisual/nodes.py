"""视听设计子图节点。

视听阶段只做视听表现增强：不改剧情、不改表演调度、不改对白含义。
一次 LLM 请求生成与 performance_direction 同结构的视听增强版最终分镜。
"""

from __future__ import annotations

from domain.directing.scene_breakdown import SceneBreakdown
from domain.directing.shot_design import ShotDesign
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
        stage=StageId.AUDIOVISUAL,
        status=EventStatus.COMPLETED,
        message=message,
        artifact_ids=artifact_ids,
    )


def audiovisual_enhancement_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    scene_breakdowns = [_ensure_scene(item) for item in state.get("scene_breakdowns", [])]
    source_shots = _source_shots_for_av(state)

    generated = generate_model_with_fallback(
        "audiovisual.enhancement",
        {
            "style_guide_summary": style_guide_summary_from_state(state),
            "audiovisual_input_summary": summarize_audiovisual_input(
                scene_breakdowns,
                source_shots,
            )
        },
        list[ShotDesign],
        fallback=lambda: build_audiovisual_enhanced_shots(source_shots),
        temperature=0.45,
    )
    enhanced_shots = _stabilize_enhanced_shots(source_shots, generated)

    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.AUDIOVISUAL_ENHANCED_SHOT_LIST,
        content=enhanced_shots,
        summary=f"{len(enhanced_shots)} 个视听增强版最终分镜。",
        created_by=NodeId.AV_ENHANCEMENT,
        parent_ref=state.get("artifact_refs", {}).get("performance_direction"),
    )
    return {
        "current_stage": StageId.AUDIOVISUAL,
        "artifact_refs": {"audiovisual_enhanced_shot_list": ref},
        "audiovisual_enhanced_shot_list": enhanced_shots,
        "events": [
            _event(
                job_id,
                NodeId.AV_ENHANCEMENT,
                "视听增强版最终分镜已生成。",
                [ref.artifact_id],
            )
        ],
    }


def build_audiovisual_package_node(state: dict) -> dict:
    job_id = state.get("job_id", "job_unknown")
    store = ArtifactStore()
    refs = state.get("artifact_refs", {})
    enhanced_shots = _enhanced_shots_for_av(state)

    package = {
        "package_id": "audiovisual_package_v001",
        "artifact_ids": {
            key: get_artifact_ref_id(ref)
            for key, ref in refs.items()
            if key in {"style_guide", "audiovisual_enhanced_shot_list"}
        },
        "source_shot_ids": [shot.shot_id for shot in _source_shots_for_av(state)],
        "enhanced_shot_ids": [shot.shot_id for shot in enhanced_shots],
        "enhanced_shot_count": len(enhanced_shots),
        "principle": (
            "保持原始剧情、对白、叙事结果和表演调度不变，"
            "只优化摄影、光影、声音和必要特效表现。"
        ),
    }
    ref = store.save(
        job_id=job_id,
        artifact_type=ArtifactType.AUDIOVISUAL_PACKAGE,
        content=package,
        summary="包含视听增强版最终分镜引用和镜头索引。",
        created_by=NodeId.AV_PACKAGE,
    )
    return {
        "current_stage": StageId.AUDIOVISUAL,
        "artifact_refs": {"audiovisual_package": ref},
        "audiovisual_package": package,
        "events": [_event(job_id, NodeId.AV_PACKAGE, "视听方案已汇总。", [ref.artifact_id])],
    }


def build_audiovisual_enhanced_shots(shots: list[ShotDesign]) -> list[ShotDesign]:
    enhanced: list[ShotDesign] = []
    for shot in shots:
        enhanced.append(
            shot.model_copy(
                update={
                    "composition": (
                        f"{shot.composition} 保持人物关系和叙事重点不变，"
                        "强化前后景层次、空间压迫感和画面纵深。"
                    ),
                    "shot_content": (
                        f"{shot.shot_content} 视听增强：不改变原有剧情、对白和表演调度。"
                        "摄影上用更克制的电影感调度服务当前情绪；光影保持统一方向和色温，"
                        "只在人物情绪拐点处加强明暗层次。声音补充与场景匹配的环境底噪、"
                        "必要动作声和轻微情绪底乐；特效仅在手机屏幕、短信、烟尘、火光等剧情确有需要时加入，"
                        "否则明确无需额外特效。"
                    ),
                    "camera_position_movement": (
                        f"{shot.camera_position_movement}；可加入轻微推拉、焦点转移或焦距变化，"
                        "但不得改变人物动作和空间站位。"
                    ),
                    "continuity": (
                        f"{shot.continuity or '承接上一镜头。'} 视听风格、光影方向、环境声、"
                        "人物站位、道具和情绪强度必须与前后镜头连续。"
                    ),
                }
            )
        )
    return enhanced


def summarize_audiovisual_input(
    scene_breakdowns: list[SceneBreakdown],
    shots: list[ShotDesign],
) -> str:
    scenes = {scene.scene_id: scene for scene in scene_breakdowns}
    lines = [
        "视听子图任务：在不改变剧情、对白、人物行为、表演调度和叙事结果的前提下，优化既有分镜的摄影、光影、声音和必要特效表现。",
        "优化原则：不要盲目加效果；只有当摄影、灯光、声音或特效能提升视频质感且不破坏叙事时才加入；保持前后镜头连贯和全片风格统一。",
        "",
        "待优化分镜：",
    ]
    for shot in shots:
        scene = scenes.get(shot.scene_id)
        if scene is not None:
            lines.extend(
                [
                    (
                        f"- 场景 {scene.scene_id}：{scene.interior_exterior}，"
                        f"{scene.location}，时间：{scene.time or '未标注'}。"
                    ),
                    f"  场景人物：{scene.characters}",
                    f"  场景道具：{scene.props}",
                    f"  服装化妆：{scene.costume_makeup}",
                    f"  场景连续性：{scene.continuity}",
                ]
            )
        lines.extend(
            [
                (
                    f"  镜头 {shot.shot_id}：第 {shot.shot_number} 镜，"
                    f"景别：{shot.shot_size}，时长：{shot.duration_seconds} 秒。"
                ),
                f"  原构图：{shot.composition}",
                f"  原镜头内容/表演调度：{shot.shot_content}",
                f"  原机位运动：{shot.camera_position_movement}",
                f"  原连续性：{shot.continuity or '未标注'}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _stabilize_enhanced_shots(
    source_shots: list[ShotDesign],
    generated_shots: list[ShotDesign],
) -> list[ShotDesign]:
    generated_by_id = {shot.shot_id: shot for shot in generated_shots}
    stabilized: list[ShotDesign] = []
    for index, source in enumerate(source_shots):
        generated = generated_by_id.get(source.shot_id)
        if generated is None and index < len(generated_shots):
            generated = generated_shots[index]
        if generated is None:
            generated = build_audiovisual_enhanced_shots([source])[0]
        stabilized.append(
            source.model_copy(
                update={
                    "composition": generated.composition or source.composition,
                    "shot_content": generated.shot_content or source.shot_content,
                    "camera_position_movement": (
                        generated.camera_position_movement
                        or source.camera_position_movement
                    ),
                    "continuity": generated.continuity or source.continuity,
                }
            )
        )
    return stabilized


def _ensure_scene(value: SceneBreakdown | dict) -> SceneBreakdown:
    return value if isinstance(value, SceneBreakdown) else SceneBreakdown(**value)


def _ensure_shot(value: ShotDesign | dict) -> ShotDesign:
    return value if isinstance(value, ShotDesign) else ShotDesign(**value)


def _source_shots_for_av(state: dict) -> list[ShotDesign]:
    performance_shots = state.get("performance_direction") or []
    source = performance_shots if performance_shots else state.get("shot_designs", [])
    return [_ensure_shot(item) for item in source]


def _enhanced_shots_for_av(state: dict) -> list[ShotDesign]:
    source = state.get("audiovisual_enhanced_shot_list") or _source_shots_for_av(state)
    return [_ensure_shot(item) for item in source]
