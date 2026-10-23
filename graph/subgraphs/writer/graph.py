"""编剧子图构建入口占位。

后续在这里组装 story_bible -> story_synopsis -> character_bible -> episode_outline -> episode_script
-> dialogue_polish -> writer_package 的 LangGraph 子图。
"""

# 作用：创建真正的 Writer LangGraph 子图。
from langgraph.graph import END, StateGraph

from graph.node_checkpoint import checkpointed_node
from graph.nodes.human_node import human_episode_outline_confirm_node
from graph.state import DramaGraphState
from graph.subgraphs.writer.edges import (
    CHARACTER_BIBLE,
    DIALOGUE_POLISH,
    EPISODE_OUTLINE,
    EPISODE_SCRIPT,
    HUMAN_EPISODE_OUTLINE_CONFIRM,
    SCRIPT_PACKAGE,
    STORY_BIBLE,
    STORY_SYNOPSIS,
    route_after_episode_outline,
)
from graph.subgraphs.writer.nodes import (
    build_script_package_node,
    create_character_bible_node,
    create_episode_outline_node,
    create_story_bible_node,
    create_story_synopsis_node,
    generate_episode_script_node,
    polish_dialogue_node,
)


# 现在 Writer 子图可以独立运行，并依次经过 7 个节点。
def build_writer_subgraph():
    builder = StateGraph(DramaGraphState)

    builder.add_node(STORY_BIBLE, checkpointed_node("writer.story_bible", create_story_bible_node))
    builder.add_node(STORY_SYNOPSIS, checkpointed_node("writer.story_synopsis", create_story_synopsis_node))
    builder.add_node(CHARACTER_BIBLE, checkpointed_node("writer.character_bible", create_character_bible_node))
    builder.add_node(EPISODE_OUTLINE, checkpointed_node("writer.episode_outline", create_episode_outline_node))
    builder.add_node(
        HUMAN_EPISODE_OUTLINE_CONFIRM,
        checkpointed_node("human_episode_outline_confirm", human_episode_outline_confirm_node),
    )
    builder.add_node(EPISODE_SCRIPT, checkpointed_node("writer.episode_script", generate_episode_script_node))
    builder.add_node(DIALOGUE_POLISH, checkpointed_node("writer.dialogue_polish", polish_dialogue_node))
    builder.add_node(SCRIPT_PACKAGE, checkpointed_node("writer.script_package", build_script_package_node))

    builder.set_entry_point(STORY_BIBLE)

    builder.add_edge(STORY_BIBLE, STORY_SYNOPSIS)
    builder.add_edge(STORY_SYNOPSIS, CHARACTER_BIBLE)
    builder.add_edge(CHARACTER_BIBLE, EPISODE_OUTLINE)
    builder.add_conditional_edges(
        EPISODE_OUTLINE,
        route_after_episode_outline,
        {
            HUMAN_EPISODE_OUTLINE_CONFIRM: HUMAN_EPISODE_OUTLINE_CONFIRM,
            EPISODE_SCRIPT: EPISODE_SCRIPT,
        },
    )
    builder.add_edge(HUMAN_EPISODE_OUTLINE_CONFIRM, END)
    builder.add_edge(EPISODE_SCRIPT, DIALOGUE_POLISH)
    builder.add_edge(DIALOGUE_POLISH, SCRIPT_PACKAGE)
    builder.add_edge(SCRIPT_PACKAGE, END)

    return builder.compile()
