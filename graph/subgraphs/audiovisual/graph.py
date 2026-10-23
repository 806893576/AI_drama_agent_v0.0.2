"""视听设计子图构建入口。"""

from langgraph.graph import END, StateGraph

from graph.node_checkpoint import checkpointed_node
from graph.state import DramaGraphState
from graph.subgraphs.audiovisual.edges import (
    AV_ENHANCEMENT,
    AV_PACKAGE,
)
from graph.subgraphs.audiovisual.nodes import (
    audiovisual_enhancement_node,
    build_audiovisual_package_node,
)


def build_audiovisual_subgraph():
    builder = StateGraph(DramaGraphState)

    builder.add_node(
        AV_ENHANCEMENT,
        checkpointed_node("audiovisual.enhancement", audiovisual_enhancement_node),
    )
    builder.add_node(
        AV_PACKAGE,
        checkpointed_node("audiovisual.package", build_audiovisual_package_node),
    )

    builder.set_entry_point(AV_ENHANCEMENT)
    builder.add_edge(AV_ENHANCEMENT, AV_PACKAGE)
    builder.add_edge(AV_PACKAGE, END)

    return builder.compile()
