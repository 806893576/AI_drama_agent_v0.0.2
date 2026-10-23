"""Tests for stable workflow enums."""

from schemas.enums import (
    ArtifactType,
    DecisionStatus,
    NodeId,
    RepairScope,
    RiskLevel,
    SafetyLayer,
    StageId,
)


def test_node_ids_cover_v4_core_flow() -> None:
    required_nodes = {
        "input_safety",
        "brief_agent",
        "style_guide",
        "producer_router",
        "writer.story_bible",
        "writer.episode_script",
        "script_reviewer",
        "quality_scoring",
        "repair_planner",
        "script_safety",
        "text_continuity",
        "director.shot_design",
        "av.enhancement",
        "shot_av_safety",
        "art_agent",
        "prompt_safety",
        "asset_manager",
        "production_continuity",
        "final_safety",
        "final_acceptance",
        "final_output",
    }

    actual_nodes = {node.value for node in NodeId}

    assert required_nodes <= actual_nodes


def test_repair_targets_use_stable_node_ids() -> None:
    assert NodeId.WRITER_EPISODE_SCRIPT.value == "writer.episode_script"
    assert NodeId.DIRECTOR_SHOT_DESIGN.value == "director.shot_design"
    assert NodeId.AV_ENHANCEMENT.value == "av.enhancement"


def test_stage_and_artifact_types_are_stable_strings() -> None:
    assert StageId.WRITER.value == "writer"
    assert StageId.AUDIOVISUAL.value == "audiovisual"
    assert ArtifactType.STYLE_GUIDE.value == "style_guide"
    assert ArtifactType.WRITER_PACKAGE.value == "writer_package"
    assert ArtifactType.AUDIOVISUAL_ENHANCED_SHOT_LIST.value == "audiovisual_enhanced_shot_list"
    assert ArtifactType.ASSET_REGISTRY.value == "asset_registry"


def test_decision_and_safety_enums_match_routing_needs() -> None:
    assert DecisionStatus.PASSED.value == "passed"
    assert DecisionStatus.NEEDS_REPAIR.value == "needs_repair"
    assert SafetyLayer.INPUT.value == "safety_l1_input"
    assert SafetyLayer.VISUAL_PROMPT.value == "safety_l3b_visual_prompt"
    assert RiskLevel.CRITICAL.value == "critical"
    assert RepairScope.PARTIAL.value == "partial"
