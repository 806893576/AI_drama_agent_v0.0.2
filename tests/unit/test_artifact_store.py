from services.storage.artifact_store import ArtifactStore
from schemas.enums import ArtifactType, NodeId


def test_artifact_store_save_and_load(tmp_path) -> None:
    store = ArtifactStore(root_dir=tmp_path)

    ref = store.save(
        job_id="job_001",
        artifact_type=ArtifactType.CREATIVE_BRIEF,
        content={"genre": "都市逆袭", "episode_count": 12},
        summary="创作简报。",
        created_by=NodeId.BRIEF_AGENT,
    )

    assert ref.artifact_id == "creative_brief_v001"
    assert store.exists(ref, job_id="job_001")

    loaded = store.load(ref, job_id="job_001")

    assert loaded.content["genre"] == "都市逆袭"
    assert loaded.summary == "创作简报。"


def test_artifact_store_increments_versions(tmp_path) -> None:
    store = ArtifactStore(root_dir=tmp_path)

    first = store.save(
        job_id="job_001",
        artifact_type=ArtifactType.WRITER_PACKAGE,
        content={"version": 1},
        created_by=NodeId.WRITER_SCRIPT_PACKAGE,
    )

    second = store.save(
        job_id="job_001",
        artifact_type=ArtifactType.WRITER_PACKAGE,
        content={"version": 2},
        created_by=NodeId.WRITER_SCRIPT_PACKAGE,
        parent_ref=first,
    )

    assert first.artifact_id == "writer_package_v001"
    assert second.artifact_id == "writer_package_v002"
    assert second.parent_artifact_id == "writer_package_v001"

    versions = store.list_versions("job_001", ArtifactType.WRITER_PACKAGE)

    assert [ref.artifact_id for ref in versions] == [
        "writer_package_v001",
        "writer_package_v002",
    ]


def test_artifact_store_supports_named_artifacts(tmp_path) -> None:
    store = ArtifactStore(root_dir=tmp_path)

    ref = store.save(
        job_id="job_001",
        artifact_type=ArtifactType.EPISODE_SCRIPT,
        name="ep_03",
        content={"episode_id": "ep_03"},
        created_by=NodeId.WRITER_EPISODE_SCRIPT,
    )

    assert ref.artifact_id == "episode_script_ep_03_v001"

    versions = store.list_versions(
        job_id="job_001",
        artifact_type=ArtifactType.EPISODE_SCRIPT,
        name="ep_03",
    )

    assert len(versions) == 1
    assert versions[0].artifact_id == "episode_script_ep_03_v001"