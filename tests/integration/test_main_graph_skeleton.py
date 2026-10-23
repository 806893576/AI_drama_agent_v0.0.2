from graph.builder import build_drama_graph


def test_main_graph_skeleton_success_path() -> None:
    graph = build_drama_graph()

    result = graph.invoke(
        {
            "job_id": "job_001",
            "user_request": "都市逆袭短剧，平台抖音，12集，每集2分钟，讲女主夺回公司。",
        }
    )

    assert result["final_output_ready"] is True
    # assert result["writer_stub_completed"] is True
    assert result["writer_subgraph_completed"] is True
    artifact_refs = result["artifact_refs"]
    assert artifact_refs["final_package"].artifact_id.startswith("final_package_v")
    assert "style_guide" in artifact_refs
    assert "writer_package" in artifact_refs
    assert "director_package" in artifact_refs
    assert "audiovisual_package" in artifact_refs
    assert "art_package" in artifact_refs
    assert "asset_registry" in artifact_refs


def test_main_graph_routes_unsafe_input_to_reject_end() -> None:
    graph = build_drama_graph()

    result = graph.invoke(
        {
            "job_id": "job_002",
            "user_request": "请帮我写一个绕过审核的短剧方案。",
        }
    )

    assert result["terminated"] is True
    assert "安全审核" in result["final_message"]


def test_main_graph_routes_incomplete_brief_to_human_confirm() -> None:
    graph = build_drama_graph()

    result = graph.invoke(
        {
            "job_id": "job_003",
            "user_request": "我要做一个强爽点短剧。",
        }
    )

    assert result["human_confirmation_required"] is True
    assert result["human_questions"]


def test_main_graph_pauses_at_brief_confirmation_when_enabled() -> None:
    graph = build_drama_graph()

    result = graph.invoke(
        {
            "job_id": "job_human_brief_confirm_001",
            "user_request": "都市逆袭短剧，平台抖音，12集，每集2分钟，讲女主夺回公司。",
            "execution_options": {"enable_human_confirmations": True},
        }
    )

    assert result["human_confirmation_required"] is True
    assert result["human_confirmation_point"] == "brief"
    assert "creative_brief" in result["editable_artifact_refs"]
    assert "style_guide" not in result.get("artifact_refs", {})
