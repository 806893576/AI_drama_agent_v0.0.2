"""LangGraph 主状态定义入口。

本文件应作为运行时 Graph State 的对外导入入口，后续可从 ``state.graph_state``
引入 DramaGraphState、ArtifactRef、ReviewStatus、ProducerDecision 等类型。

设计原则：
- 只保存轻量运行态字段和产物引用。
- 不保存完整剧本、分镜、Prompt 等长文本。
- 所有长文本进入 Artifact Store，所有角色/场景/道具/镜头等进入 Asset Registry。
"""

# 作用：让 LangGraph 层可以从统一入口导入 DramaGraphState。
"""
后续 graph/builder.py 里可以写：
from graph.state import DramaGraphState
而不是直接引用 state.graph_state。
"""
from state.graph_state import DramaGraphState

__all__ = ["DramaGraphState"]