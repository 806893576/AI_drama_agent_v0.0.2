"""导演子图构建入口。"""

from langgraph.graph import END, StateGraph

from graph.node_checkpoint import checkpointed_node
from graph.state import DramaGraphState
from graph.subgraphs.director.edges import (
    DIRECTOR_PACKAGE,
    PERFORMANCE,
    SCENE_BREAKDOWN,
    SHOT_DESIGN,
)
from graph.subgraphs.director.nodes import (
    build_director_package_node,
    performance_direction_node,
    scene_breakdown_node,
    shot_design_node,
)


def build_director_subgraph():
    builder = StateGraph(DramaGraphState)

    builder.add_node(
        SCENE_BREAKDOWN,
        checkpointed_node("director.scene_breakdown", scene_breakdown_node),
    )
    builder.add_node(SHOT_DESIGN, checkpointed_node("director.shot_design", shot_design_node))
    builder.add_node(
        PERFORMANCE,
        checkpointed_node("director.performance", performance_direction_node),
    )
    builder.add_node(
        DIRECTOR_PACKAGE,
        checkpointed_node("director.package", build_director_package_node),
    )

    builder.set_entry_point(SCENE_BREAKDOWN)
    builder.add_edge(SCENE_BREAKDOWN, SHOT_DESIGN)
    builder.add_edge(SHOT_DESIGN, PERFORMANCE)
    builder.add_edge(PERFORMANCE, DIRECTOR_PACKAGE)
    builder.add_edge(DIRECTOR_PACKAGE, END)

    return builder.compile()
