from schemas.enums import (
    ArtifactType,
    DecisionStatus,
    EventStatus,
    NodeId,
    ProducerMode,
    StageId,
)
from state.artifact_refs import ArtifactRef
from state.events import RuntimeEvent
from state.producer_decision import ProducerDecision
from state.reducers import append_events, merge_artifact_refs, merge_retry_counts


def test_artifact_ref_keeps_lightweight_reference() -> None:
    ref = ArtifactRef(
        artifact_id="writer_package_v001",
        artifact_type=ArtifactType.WRITER_PACKAGE,
        version=1,
        summary="编剧阶段产物包。",
        created_by=NodeId.WRITER_SCRIPT_PACKAGE,
    )

    assert ref.artifact_id == "writer_package_v001"
    assert ref.artifact_type == ArtifactType.WRITER_PACKAGE


def test_producer_decision_is_structured() -> None:
    decision = ProducerDecision(
        status=DecisionStatus.NEEDS_REPAIR,
        mode=ProducerMode.REPAIR,
        next_node=NodeId.LOCAL_REPAIR_ROUTER,
        reason="质量评分未达标。",
    )

    assert decision.next_node == NodeId.LOCAL_REPAIR_ROUTER


def test_runtime_event_defaults_to_timestamp() -> None:
    event = RuntimeEvent(
        event_id="evt_001",
        node_id=NodeId.BRIEF_AGENT,
        stage=StageId.BRIEF,
        status=EventStatus.COMPLETED,
        message="Creative brief generated.",
        artifact_ids=["brief_v001"],
    )

    assert event.artifact_ids == ["brief_v001"]
    assert event.created_at is not None


def test_state_reducers_merge_expected_fields() -> None:
    current_refs = {
        "writer_package": ArtifactRef(
            artifact_id="writer_package_v001",
            artifact_type=ArtifactType.WRITER_PACKAGE,
            version=1,
        )
    }
    update_refs = {
        "writer_package": ArtifactRef(
            artifact_id="writer_package_v002",
            artifact_type=ArtifactType.WRITER_PACKAGE,
            version=2,
        )
    }

    merged_refs = merge_artifact_refs(current_refs, update_refs)

    assert merged_refs["writer_package"].artifact_id == "writer_package_v002"

    retry_counts = merge_retry_counts(
        {"writer.episode_script": 1},
        {"writer.episode_script": 1, "art_agent": 1},
    )

    assert retry_counts["writer.episode_script"] == 2
    assert retry_counts["art_agent"] == 1

    events = append_events(["a"], ["b"])

    assert events == ["a", "b"]