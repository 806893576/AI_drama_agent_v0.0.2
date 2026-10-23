"""模块级工作流入口。

用于从已落盘的上游 artifact 启动导演或视听子图，避免每次调试都重跑完整主链路。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from langgraph.graph import END, StateGraph

from database.connection import JsonDatabase
from database.models import JobRecord
from domain.directing.scene_breakdown import SceneBreakdown
from domain.directing.shot_design import ShotDesign
from domain.story.character_bible import CharacterBible
from domain.story.episode_script import EpisodeScript
from domain.style import CreativeStyleGuide
from graph.node_checkpoint import checkpointed_node
from graph.nodes.art_asset_nodes import art_agent_node
from graph.state import DramaGraphState
from graph.subgraphs.audiovisual.graph import build_audiovisual_subgraph
from graph.subgraphs.director.graph import build_director_subgraph
from schemas.enums import ArtifactType
from services.llm import (
    LLMRuntimeError,
    LLMStructuredOutputError,
    llm_trace_context,
    structured_output_mode,
)
from services.storage.artifact_store import ArtifactStore
from state.artifact_refs import ArtifactRef, get_artifact_ref_id


@dataclass(slots=True)
class ModuleRunResult:
    state: dict[str, Any]
    summary: dict[str, Any]


def run_director_generation(
    *,
    source_job_id: str,
    output_job_id: str | None = None,
    episode_script_artifact_id: str | None = None,
    llm_format_mode: str = "interrupt",
) -> ModuleRunResult:
    """从 episode_script artifact 单独启动导演子图。"""

    store = ArtifactStore()
    run_job_id = output_job_id or _new_module_job_id(source_job_id, "director")
    episode_script_ref = _resolve_artifact_ref(
        store,
        job_id=source_job_id,
        artifact_type=ArtifactType.EPISODE_SCRIPT,
        artifact_id=episode_script_artifact_id,
    )
    episode_scripts = _coerce_model_list(
        store.load(episode_script_ref, job_id=source_job_id).content,
        EpisodeScript,
    )
    style_guide_ref = _resolve_optional_latest_ref(
        store,
        job_id=source_job_id,
        artifact_type=ArtifactType.STYLE_GUIDE,
    )
    initial_state = {
        "job_id": run_job_id,
        "source_job_id": source_job_id,
        "artifact_refs": {"episode_script": episode_script_ref},
        "episode_scripts": episode_scripts,
        "completed_nodes": [],
        "resume_mode": False,
        "resume_from_checkpoint": False,
        "events": [],
    }
    input_artifact_refs = {"episode_script": episode_script_ref}
    if style_guide_ref is not None:
        initial_state["artifact_refs"]["style_guide"] = style_guide_ref
        initial_state["style_guide"] = _coerce_model(
            store.load(style_guide_ref, job_id=source_job_id).content,
            CreativeStyleGuide,
        )
        input_artifact_refs["style_guide"] = style_guide_ref
    return _run_module_subgraph(
        graph=build_director_subgraph(),
        initial_state=initial_state,
        module="director",
        source_job_id=source_job_id,
        output_job_id=run_job_id,
        input_artifact_refs=input_artifact_refs,
        llm_format_mode=llm_format_mode,
        output_artifact_key="director_package",
    )


def run_audiovisual_generation(
    *,
    source_job_id: str,
    output_job_id: str | None = None,
    performance_direction_artifact_id: str | None = None,
    llm_format_mode: str = "interrupt",
) -> ModuleRunResult:
    """从 performance_direction artifact 单独启动视听子图。"""

    store = ArtifactStore()
    run_job_id = output_job_id or _new_module_job_id(source_job_id, "av")
    performance_direction_ref = _resolve_artifact_ref(
        store,
        job_id=source_job_id,
        artifact_type=ArtifactType.PERFORMANCE_DIRECTION,
        artifact_id=performance_direction_artifact_id,
    )
    performance_direction = _coerce_model_list(
        store.load(performance_direction_ref, job_id=source_job_id).content,
        ShotDesign,
    )
    style_guide_ref = _resolve_optional_latest_ref(
        store,
        job_id=source_job_id,
        artifact_type=ArtifactType.STYLE_GUIDE,
    )

    initial_state = {
        "job_id": run_job_id,
        "source_job_id": source_job_id,
        "artifact_refs": {"performance_direction": performance_direction_ref},
        "performance_direction": performance_direction,
        "completed_nodes": [],
        "resume_mode": False,
        "resume_from_checkpoint": False,
        "events": [],
    }
    input_artifact_refs = {"performance_direction": performance_direction_ref}
    if style_guide_ref is not None:
        initial_state["artifact_refs"]["style_guide"] = style_guide_ref
        initial_state["style_guide"] = _coerce_model(
            store.load(style_guide_ref, job_id=source_job_id).content,
            CreativeStyleGuide,
        )
        input_artifact_refs["style_guide"] = style_guide_ref
    return _run_module_subgraph(
        graph=build_audiovisual_subgraph(),
        initial_state=initial_state,
        module="audiovisual",
        source_job_id=source_job_id,
        output_job_id=run_job_id,
        input_artifact_refs=input_artifact_refs,
        llm_format_mode=llm_format_mode,
        output_artifact_key="audiovisual_package",
    )


def run_art_generation(
    *,
    source_job_id: str,
    output_job_id: str | None = None,
    scene_breakdown_job_id: str | None = None,
    scene_breakdown_artifact_id: str | None = None,
    audiovisual_enhanced_shot_list_job_id: str | None = None,
    audiovisual_enhanced_shot_list_artifact_id: str | None = None,
    character_bible_job_id: str | None = None,
    character_bible_artifact_id: str | None = None,
    llm_format_mode: str = "interrupt",
) -> ModuleRunResult:
    """从 scene_breakdown 与 audiovisual_enhanced_shot_list 单独启动美术组 Agent。"""

    store = ArtifactStore()
    run_job_id = output_job_id or _new_module_job_id(source_job_id, "art")
    scene_job_id = scene_breakdown_job_id or source_job_id
    shot_job_id = audiovisual_enhanced_shot_list_job_id or source_job_id

    scene_breakdown_ref = _resolve_artifact_ref(
        store,
        job_id=scene_job_id,
        artifact_type=ArtifactType.SCENE_BREAKDOWN,
        artifact_id=scene_breakdown_artifact_id,
    )
    enhanced_shot_ref = _resolve_artifact_ref(
        store,
        job_id=shot_job_id,
        artifact_type=ArtifactType.AUDIOVISUAL_ENHANCED_SHOT_LIST,
        artifact_id=audiovisual_enhanced_shot_list_artifact_id,
    )
    scene_breakdowns = _coerce_model_list(
        store.load(scene_breakdown_ref, job_id=scene_job_id).content,
        SceneBreakdown,
    )
    enhanced_shots = _coerce_model_list(
        store.load(enhanced_shot_ref, job_id=shot_job_id).content,
        ShotDesign,
    )
    character_bible_ref = None
    character_bible = None
    if character_bible_job_id is not None or character_bible_artifact_id is not None:
        character_job_id = character_bible_job_id or source_job_id
        character_bible_ref = _resolve_artifact_ref(
            store,
            job_id=character_job_id,
            artifact_type=ArtifactType.CHARACTER_BIBLE,
            artifact_id=character_bible_artifact_id,
        )
        character_bible = _coerce_model(
            store.load(character_bible_ref, job_id=character_job_id).content,
            CharacterBible,
        )

    initial_state = {
        "job_id": run_job_id,
        "source_job_id": source_job_id,
        "artifact_refs": {
            "scene_breakdown": scene_breakdown_ref,
            "audiovisual_enhanced_shot_list": enhanced_shot_ref,
        },
        "scene_breakdowns": scene_breakdowns,
        "audiovisual_enhanced_shot_list": enhanced_shots,
        "completed_nodes": [],
        "resume_mode": False,
        "resume_from_checkpoint": False,
        "events": [],
    }
    input_artifact_refs = {
        "scene_breakdown": scene_breakdown_ref,
        "audiovisual_enhanced_shot_list": enhanced_shot_ref,
    }
    if character_bible_ref is not None:
        initial_state["artifact_refs"]["character_bible"] = character_bible_ref
        initial_state["character_bible"] = character_bible
        input_artifact_refs["character_bible"] = character_bible_ref
    style_guide_ref = _resolve_optional_latest_ref(
        store,
        job_id=source_job_id,
        artifact_type=ArtifactType.STYLE_GUIDE,
    )
    if style_guide_ref is not None:
        initial_state["artifact_refs"]["style_guide"] = style_guide_ref
        initial_state["style_guide"] = _coerce_model(
            store.load(style_guide_ref, job_id=source_job_id).content,
            CreativeStyleGuide,
        )
        input_artifact_refs["style_guide"] = style_guide_ref

    return _run_module_subgraph(
        graph=_build_art_agent_subgraph(),
        initial_state=initial_state,
        module="art",
        source_job_id=source_job_id,
        output_job_id=run_job_id,
        input_artifact_refs=input_artifact_refs,
        llm_format_mode=llm_format_mode,
        output_artifact_key="art_package",
    )


def _build_art_agent_subgraph():
    builder = StateGraph(DramaGraphState)
    builder.add_node("art_agent", checkpointed_node("art_agent", art_agent_node))
    builder.set_entry_point("art_agent")
    builder.add_edge("art_agent", END)
    return builder.compile()


def _run_module_subgraph(
    *,
    graph: Any,
    initial_state: dict[str, Any],
    module: str,
    source_job_id: str,
    output_job_id: str,
    input_artifact_refs: dict[str, ArtifactRef],
    llm_format_mode: str,
    output_artifact_key: str,
) -> ModuleRunResult:
    try:
        with llm_trace_context(output_job_id), structured_output_mode(llm_format_mode):
            state = graph.invoke(initial_state)
    except LLMStructuredOutputError as exc:
        state = _build_module_pause_state(
            initial_state=initial_state,
            error=exc,
            error_kind="format",
        )
    except LLMRuntimeError as exc:
        state = _build_module_pause_state(
            initial_state=initial_state,
            error=exc,
            error_kind="runtime",
        )

    summary = _summarize_module_result(
        state,
        module=module,
        source_job_id=source_job_id,
        output_job_id=output_job_id,
        input_artifact_refs=input_artifact_refs,
        output_artifact_key=output_artifact_key,
    )
    _save_module_job_record(summary)
    return ModuleRunResult(state=state, summary=summary)


def _build_module_pause_state(
    *,
    initial_state: dict[str, Any],
    error: LLMStructuredOutputError | LLMRuntimeError,
    error_kind: str,
) -> dict[str, Any]:
    state = dict(initial_state)
    state["human_confirmation_required"] = True
    state["module_output_ready"] = False
    if error_kind == "format":
        state["final_message"] = (
            f"模块运行暂停：{error.prompt_id} 结构化输出失败。"
            "可确认后使用 auto_repair 重新运行该模块。"
        )
        state["llm_format_error"] = error.to_summary()
        state["llm_repair_available"] = True
        state["llm_runtime_error"] = None
        state["llm_retry_available"] = False
    else:
        state["final_message"] = f"模块运行暂停：{error.prompt_id} LLM 请求失败。"
        state["llm_format_error"] = None
        state["llm_repair_available"] = False
        state["llm_runtime_error"] = error.to_summary()
        state["llm_retry_available"] = True
    return state


def _summarize_module_result(
    state: dict[str, Any],
    *,
    module: str,
    source_job_id: str,
    output_job_id: str,
    input_artifact_refs: dict[str, ArtifactRef],
    output_artifact_key: str,
) -> dict[str, Any]:
    artifact_refs = state.get("artifact_refs", {})
    events = state.get("events", [])
    module_output_ready = output_artifact_key in artifact_refs and not state.get(
        "human_confirmation_required",
        False,
    )
    return {
        "job_id": output_job_id,
        "source_job_id": source_job_id,
        "module": module,
        "module_output_ready": module_output_ready,
        "status": "completed" if module_output_ready else "paused_or_rejected",
        "final_message": state.get("final_message"),
        "human_confirmation_required": state.get("human_confirmation_required", False),
        "llm_format_error": state.get("llm_format_error"),
        "llm_repair_available": state.get("llm_repair_available", False),
        "llm_runtime_error": state.get("llm_runtime_error"),
        "llm_retry_available": state.get("llm_retry_available", False),
        "completed_nodes": state.get("completed_nodes", []),
        "last_completed_node": state.get("last_completed_node"),
        "input_artifact_ids": {
            key: get_artifact_ref_id(ref) for key, ref in input_artifact_refs.items()
        },
        "artifact_ids": {
            key: get_artifact_ref_id(ref) for key, ref in artifact_refs.items()
        },
        "event_count": len(events),
    }


def _save_module_job_record(summary: dict[str, Any]) -> None:
    JsonDatabase().save_job(
        JobRecord(
            job_id=summary["job_id"],
            user_request=f"{summary['module']} module run from {summary['source_job_id']}",
            status=summary["status"],
            final_message=summary.get("final_message"),
            artifact_ids=summary.get("artifact_ids", {}),
            event_count=summary.get("event_count", 0),
        )
    )


def _resolve_artifact_ref(
    store: ArtifactStore,
    *,
    job_id: str,
    artifact_type: ArtifactType,
    artifact_id: str | None = None,
) -> ArtifactRef:
    refs = store.list_versions(job_id, artifact_type)
    if artifact_id:
        for ref in refs:
            if ref.artifact_id == artifact_id:
                return ref
        raise FileNotFoundError(
            f"Artifact not found: job_id={job_id}, type={artifact_type.value}, id={artifact_id}"
        )
    if not refs:
        raise FileNotFoundError(
            f"No artifact found: job_id={job_id}, type={artifact_type.value}"
        )
    return max(refs, key=lambda ref: ref.version)


def _resolve_optional_latest_ref(
    store: ArtifactStore,
    *,
    job_id: str,
    artifact_type: ArtifactType,
) -> ArtifactRef | None:
    refs = store.list_versions(job_id, artifact_type)
    if not refs:
        return None
    return max(refs, key=lambda ref: ref.version)


def _coerce_model_list(value: Any, model_type: type) -> list[Any]:
    items = value if isinstance(value, list) else [value]
    return [item if isinstance(item, model_type) else model_type(**item) for item in items]


def _coerce_model(value: Any, model_type: type) -> Any:
    return value if isinstance(value, model_type) else model_type(**value)


def _new_module_job_id(source_job_id: str, module: str) -> str:
    return f"{source_job_id}_{module}_{uuid4().hex[:8]}"
