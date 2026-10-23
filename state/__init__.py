"""分层状态管理包。

Graph State 只保存轻量字段和产物引用；长文本进入 Artifact Store；资产进入 Asset Registry。
"""

from state.artifact_refs import ArtifactRef
from state.events import RuntimeEvent
from state.graph_state import DramaGraphState
from state.producer_decision import ProducerDecision

__all__ = [
    "ArtifactRef",
    "DramaGraphState",
    "ProducerDecision",
    "RuntimeEvent",
]