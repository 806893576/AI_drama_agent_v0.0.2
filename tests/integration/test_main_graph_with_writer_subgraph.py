from graph.builder import build_drama_graph


def test_main_graph_uses_writer_subgraph_skeleton() -> None:
    graph = build_drama_graph()

    result = graph.invoke(
        {
            "job_id": "job_main_writer_001",
            "user_request": "都市逆袭短剧，平台抖音，12集，每集2分钟，讲女主夺回公司。",
        }
    )

    artifact_refs = result["artifact_refs"]

    assert result["final_output_ready"] is True
    assert result["writer_subgraph_completed"] is True
    assert "story_bible" in artifact_refs
    assert "writer_package" in artifact_refs