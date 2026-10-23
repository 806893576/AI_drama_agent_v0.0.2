"""功能：数据模型包，定义 Agent 平台内部流转和 API 暴露的数据结构。"""
"""Shared schemas for API, graph state, artifacts, and routing."""

# 作用：统一导出核心枚举，方便后续模块引用。
"""
后续可以写：
from schemas import NodeId, ArtifactType
"""
from schemas.enums import (
    ArtifactType,
    DecisionStatus,
    EventStatus,
    IssueType,
    NodeId,
    ProducerMode,
    RepairScope,
    ReviewType,
    RiskLevel,
    SafetyLayer,
    StageId,
)

__all__ = [
    "ArtifactType",
    "DecisionStatus",
    "EventStatus",
    "IssueType",
    "NodeId",
    "ProducerMode",
    "RepairScope",
    "ReviewType",
    "RiskLevel",
    "SafetyLayer",
    "StageId",
]