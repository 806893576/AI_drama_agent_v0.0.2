"""短剧生成主图构建入口。

主图参考 drama-agent-flow-v4.html：
输入安全 -> 需求分析 -> 制片调度 -> 编剧子图 -> 审核/返工 ->
导演子图 -> 视听子图 -> 美术/资产 -> 制作一致性 -> 最终安全 -> 验收 -> 输出。
"""

from langgraph.graph import END, StateGraph

from graph.edges import (
    route_after_art_agent,
    route_after_asset_manager,
    route_after_audiovisual_subgraph,
    route_after_brief_gate,
    route_after_final_acceptance,
    route_after_final_safety,
    route_after_input_safety,
    route_after_local_repair_router,
    route_after_producer,
    route_after_production_continuity,
    route_after_prompt_safety,
    route_after_quality_scoring,
    route_after_script_reviewer,
    route_after_script_safety,
    route_after_shot_av_safety,
    route_after_style_guide,
    route_after_text_continuity,
    route_after_writer_subgraph,
)
from graph.node_checkpoint import checkpointed_node
from graph.nodes.agent_node import brief_agent_node
from graph.nodes.art_asset_nodes import art_agent_node, asset_manager_node
from graph.nodes.final_output_node import final_output_node
from graph.nodes.human_node import (
    brief_gate_node,
    human_brief_confirm_node,
    human_confirm_node,
    human_style_confirm_node,
    reject_end_node,
)
from graph.nodes.input_node import input_safety_node
from graph.nodes.producer_router_node import local_repair_router_node, producer_router_node
from graph.nodes.repair_node import repair_planner_node
from graph.nodes.review_nodes import (
    final_acceptance_node,
    final_safety_node,
    production_continuity_node,
    prompt_safety_node,
    quality_scoring_node,
    script_reviewer_node,
    script_safety_node,
    shot_av_safety_node,
    text_continuity_node,
)
from graph.nodes.style_guide_node import style_guide_node
from graph.state import DramaGraphState
from graph.subgraphs.audiovisual.graph import build_audiovisual_subgraph
from graph.subgraphs.director.graph import build_director_subgraph
from graph.subgraphs.writer.graph import build_writer_subgraph


def build_drama_graph():
    builder = StateGraph(DramaGraphState)

    # 输入与制片调度
    builder.add_node("input_safety", checkpointed_node("input_safety", input_safety_node))
    builder.add_node("brief_agent", checkpointed_node("brief_agent", brief_agent_node))
    builder.add_node("brief_gate", checkpointed_node("brief_gate", brief_gate_node))
    builder.add_node("style_guide", checkpointed_node("style_guide", style_guide_node))
    builder.add_node("human_confirm", checkpointed_node("human_confirm", human_confirm_node))
    builder.add_node(
        "human_brief_confirm",
        checkpointed_node("human_brief_confirm", human_brief_confirm_node),
    )
    builder.add_node(
        "human_style_confirm",
        checkpointed_node("human_style_confirm", human_style_confirm_node),
    )
    builder.add_node("reject_end", checkpointed_node("reject_end", reject_end_node))
    builder.add_node("producer_router", checkpointed_node("producer_router", producer_router_node))
    builder.add_node(
        "local_repair_router",
        checkpointed_node("local_repair_router", local_repair_router_node),
    )
    builder.add_node("repair_planner", checkpointed_node("repair_planner", repair_planner_node))

    # 创作与制作子图（编剧、导演、视听子图）
    builder.add_node("writer_subgraph", build_writer_subgraph())
    builder.add_node("director_subgraph", build_director_subgraph())
    builder.add_node("audiovisual_subgraph", build_audiovisual_subgraph())

    # 审核、资产与最终输出
    builder.add_node("script_reviewer", checkpointed_node("script_reviewer", script_reviewer_node))
    builder.add_node("quality_scoring", checkpointed_node("quality_scoring", quality_scoring_node))
    builder.add_node("script_safety", checkpointed_node("script_safety", script_safety_node))
    builder.add_node("text_continuity", checkpointed_node("text_continuity", text_continuity_node))
    builder.add_node("shot_av_safety", checkpointed_node("shot_av_safety", shot_av_safety_node))
    builder.add_node("art_agent", checkpointed_node("art_agent", art_agent_node))
    builder.add_node("prompt_safety", checkpointed_node("prompt_safety", prompt_safety_node))
    builder.add_node("asset_manager", checkpointed_node("asset_manager", asset_manager_node))
    builder.add_node(
        "production_continuity",
        checkpointed_node("production_continuity", production_continuity_node),
    )
    builder.add_node("final_safety", checkpointed_node("final_safety", final_safety_node))
    builder.add_node(
        "final_acceptance",
        checkpointed_node("final_acceptance", final_acceptance_node),
    )
    builder.add_node("final_output", checkpointed_node("final_output", final_output_node))

    builder.set_entry_point("input_safety") # 设置起始点

    builder.add_conditional_edges(
        "input_safety",
        route_after_input_safety,
        {
            "brief_agent": "brief_agent",
            "input_rewrite": "human_confirm",
            "reject_end": "reject_end",
        },
    )
    builder.add_edge("brief_agent", "brief_gate")
    builder.add_conditional_edges(
        "brief_gate",
        route_after_brief_gate,
        {
            "producer_router": "style_guide",
            "human_brief_confirm": "human_brief_confirm",
            "human_confirm": "human_confirm",
        },
    )
    builder.add_conditional_edges(
        "style_guide",
        route_after_style_guide,
        {
            "producer_router": "producer_router",
            "human_style_confirm": "human_style_confirm",
        },
    )
    builder.add_conditional_edges(
        "producer_router",
        route_after_producer,
        {
            "writer.story_bible": "writer_subgraph",
            "local_repair_router": "local_repair_router",
            "human_confirm": "human_confirm",
            "final_output": "final_output",
        },
    )

    # 正常主路径
    builder.add_conditional_edges(
        "writer_subgraph",
        route_after_writer_subgraph,
        {
            "script_reviewer": "script_reviewer",
            "quality_scoring": "quality_scoring",
            "script_safety": "script_safety",
            "text_continuity": "text_continuity",
            "director.scene_breakdown": "director_subgraph",
            "human_confirm": "human_confirm",
        },
    )
    builder.add_conditional_edges(
        "script_reviewer",
        route_after_script_reviewer,
        {
            "quality_scoring": "quality_scoring",
            "script_safety": "script_safety",
            "text_continuity": "text_continuity",
            "director.scene_breakdown": "director_subgraph",
        },
    )
    builder.add_conditional_edges(
        "quality_scoring",
        route_after_quality_scoring,
        {
            "script_safety": "script_safety",
            "text_continuity": "text_continuity",
            "director.scene_breakdown": "director_subgraph",
            "repair_planner": "repair_planner",
        },
    )
    builder.add_conditional_edges(
        "script_safety",
        route_after_script_safety,
        {
            "text_continuity": "text_continuity",
            "director.scene_breakdown": "director_subgraph",
            "repair_planner": "repair_planner",
        },
    )
    builder.add_conditional_edges(
        "text_continuity",
        route_after_text_continuity,
        {"director.scene_breakdown": "director_subgraph", "repair_planner": "repair_planner"},
    )
    builder.add_edge("director_subgraph", "audiovisual_subgraph")
    builder.add_conditional_edges(
        "audiovisual_subgraph",
        route_after_audiovisual_subgraph,
        {"shot_av_safety": "shot_av_safety", "art_agent": "art_agent"},
    )
    builder.add_conditional_edges(
        "shot_av_safety",
        route_after_shot_av_safety,
        {"art_agent": "art_agent", "repair_planner": "repair_planner"},
    )
    builder.add_conditional_edges(
        "art_agent",
        route_after_art_agent,
        {"prompt_safety": "prompt_safety", "asset_manager": "asset_manager"},
    )
    builder.add_conditional_edges(
        "prompt_safety",
        route_after_prompt_safety,
        {"asset_manager": "asset_manager", "repair_planner": "repair_planner"},
    )
    builder.add_conditional_edges(
        "asset_manager",
        route_after_asset_manager,
        {
            "production_continuity": "production_continuity",
            "final_safety": "final_safety",
            "final_acceptance": "final_acceptance",
            "final_output": "final_output",
        },
    )
    builder.add_conditional_edges(
        "production_continuity",
        route_after_production_continuity,
        {
            "final_safety": "final_safety",
            "final_acceptance": "final_acceptance",
            "final_output": "final_output",
            "repair_planner": "repair_planner",
        },
    )
    builder.add_conditional_edges(
        "final_safety",
        route_after_final_safety,
        {
            "final_acceptance": "final_acceptance",
            "final_output": "final_output",
            "repair_planner": "repair_planner",
        },
    )
    builder.add_conditional_edges(
        "final_acceptance",
        route_after_final_acceptance,
        {"final_output": "final_output", "repair_planner": "repair_planner"},
    )

    # 返工路径：Repair Planner 产出 target_node，Local Repair Router 再映射到对应模块。
    builder.add_edge("repair_planner", "local_repair_router")
    builder.add_conditional_edges(
        "local_repair_router",
        route_after_local_repair_router,
        {
            "writer.story_bible": "writer_subgraph",
            "writer.episode_script": "writer_subgraph",
            "writer.dialogue_polish": "writer_subgraph",
            "director.shot_design": "director_subgraph",
            "av.enhancement": "audiovisual_subgraph",
            "art_agent": "art_agent",
            "asset_manager": "asset_manager",
            "human_confirm": "human_confirm",
        },
    )

    builder.add_edge("final_output", END)
    builder.add_edge("human_confirm", END)
    builder.add_edge("human_brief_confirm", END)
    builder.add_edge("human_style_confirm", END)
    builder.add_edge("reject_end", END)

    return builder.compile()
