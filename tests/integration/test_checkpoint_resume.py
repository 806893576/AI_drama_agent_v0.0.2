from __future__ import annotations

from uuid import uuid4

import pytest

import graph.subgraphs.writer.graph as writer_graph
import workflows.generation_workflow as generation_workflow
from graph.execution_options import ExecutionOptions
from graph.subgraphs.writer.nodes import create_character_bible_node
from memory.checkpoint import JsonCheckpointStore
from services.llm import LLMRuntimeError
from workflows.generation_workflow import run_generation


def test_runtime_retry_resumes_from_failed_writer_node(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = f"job_resume_{uuid4().hex[:8]}"
    user_request = "都市逆袭短剧，平台抖音，12集，每集2分钟，女主被夺走公司后重新夺回主动权。"

    def fail_character_bible(_state: dict) -> dict:
        raise LLMRuntimeError(prompt_id="writer.character_bible", error_message="simulated timeout")

    monkeypatch.setattr(writer_graph, "create_character_bible_node", fail_character_bible)

    first = run_generation(user_request=user_request, job_id=job_id)

    assert first.summary["final_output_ready"] is False
    assert first.summary["llm_retry_available"] is True
    assert first.summary["llm_runtime_error"]["prompt_id"] == "writer.character_bible"
    assert "writer.story_bible" in first.summary["completed_nodes"]
    assert "writer.story_synopsis" in first.summary["completed_nodes"]
    assert "writer.character_bible" not in first.summary["completed_nodes"]
    assert first.summary["artifact_ids"]["story_bible"] == "story_bible_v001"
    assert first.summary["artifact_ids"]["story_synopsis"] == "story_synopsis_v001"

    checkpoint = JsonCheckpointStore().load(job_id)
    assert checkpoint["artifact_refs"]["story_bible"]["artifact_id"] == "story_bible_v001"
    assert checkpoint["artifact_refs"]["story_synopsis"]["artifact_id"] == "story_synopsis_v001"

    monkeypatch.setattr(writer_graph, "create_character_bible_node", create_character_bible_node)

    second = run_generation(
        user_request=user_request,
        job_id=job_id,
        resume_from_checkpoint=True,
    )

    assert second.summary["final_output_ready"] is True
    assert second.summary["resume_from_checkpoint"] is True
    assert second.summary["artifact_ids"]["story_bible"] == "story_bible_v001"
    assert second.summary["artifact_ids"]["story_synopsis"] == "story_synopsis_v001"
    assert second.summary["artifact_ids"]["character_bible"] == "character_bible_v001"
    assert "final_package" in second.summary["artifact_ids"]


def test_resume_reuses_checkpoint_execution_options_when_not_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = f"job_resume_options_{uuid4().hex[:8]}"
    user_request = "都市逆袭短剧，平台抖音，3集，每集2分钟。"
    checkpoint_options = ExecutionOptions.fast_draft().model_dump(mode="json")
    JsonCheckpointStore().save(
        job_id,
        {
            "job_id": job_id,
            "user_request": user_request,
            "execution_options": checkpoint_options,
            "completed_nodes": ["writer.episode_script"],
            "artifact_refs": {},
            "events": [],
        },
    )
    captured: dict[str, object] = {}

    class FakeGraph:
        def invoke(self, state: dict) -> dict:
            captured["execution_options"] = state["execution_options"]
            return {
                **state,
                "final_output_ready": True,
                "artifact_refs": {},
                "events": [],
            }

    monkeypatch.setattr(generation_workflow, "build_drama_graph", lambda: FakeGraph())

    result = run_generation(
        user_request=user_request,
        job_id=job_id,
        resume_from_checkpoint=True,
    )

    assert result.summary["resume_from_checkpoint"] is True
    assert captured["execution_options"]["run_script_review"] is False
    assert captured["execution_options"]["skipped_reason"] == "fast_draft"
