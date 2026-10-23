"""作用：所有审核报告都会复用 ReviewFinding，避免每个审核模型重复定义问题结构。"""

from pydantic import BaseModel, Field

from schemas.enums import IssueType, NodeId, RiskLevel


"""
    问题类型是什么？
    严重程度是什么？
    证据在哪里？
    影响哪些产物？
    建议返工到哪个节点？
    建议怎么改？
"""
"""
    issue_type: 问题类型（类型为枚举 IssueType，例如逻辑漏洞、安全违规、对白不自然、风格不符等）。
    severity: 严重程度（类型为枚举 RiskLevel，例如轻微、严重、致命风险，用于决定是否需要立即拦截工作流）。
    description: 问题的详细描述说明（具体阐述发生了什么问题）。
    evidence: 证据列表（默认空列表，用于记录触发该问题的原文片段、对话或画面描述，做到有据可查）。
    affected_artifacts: 受影响的产物列表（默认空列表，记录该问题波及了哪些剧本、分镜或资产）。
    suggested_target_node: 建议返工的目标节点（类型为枚举 NodeId，可选。指明如果修复这个问题，工作流应该回滚到哪一个历史节点重新执行，如回到编剧节点或对白润色节点）。
    suggested_changes: 建议修改方案列表（默认空列表，为后续的 Agent 或人工修改提供具体的整改建议）。
"""
class ReviewFinding(BaseModel):
    issue_type: IssueType
    severity: RiskLevel
    description: str
    evidence: list[str] = Field(default_factory=list)
    affected_artifacts: list[str] = Field(default_factory=list)
    suggested_target_node: NodeId | None = None
    suggested_changes: list[str] = Field(default_factory=list)