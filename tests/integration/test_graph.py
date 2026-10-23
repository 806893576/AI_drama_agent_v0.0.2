from graph.builder import build_drama_graph


def test_graph_can_compile() -> None:
    graph = build_drama_graph()

    assert graph is not None
