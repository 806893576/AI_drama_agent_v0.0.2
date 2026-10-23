"""安全合规审核报告模型占位。

用于记录输入、剧本、镜头、视听、视觉 Prompt、版权/IP 风险等分级审核结果。
"""
"""
具体作用：
安全审核失败后，不直接跳回创作节点，而是把这个报告交给 Repair Planner。
例如：
    Prompt 安全失败 -> repair_target = NodeId.ART_AGENT
    镜头安全失败 -> repair_target = NodeId.DIRECTOR_SHOT_DESIGN 或 NodeId.AV_VFX
    剧本安全失败 -> repair_target = NodeId.WRITER_DIALOGUE_POLISH
"""

# 作用：支持 V4 里的分级安全审核：输入、剧本、镜头/视听、视觉 Prompt、最终安全。
from pydantic import BaseModel, Field

from domain.review.base import ReviewFinding
from schemas.enums import NodeId, RiskLevel, SafetyLayer


"""
承载安全审核/风控检查 Agent 的输出报告
    report_id: 安全报告的唯一标识符。
    layer: 当前执行检查的安全层级（类型为枚举 SafetyLayer，例如输入端审核、L3B 视觉提示词安全等，用于区分在哪个阶段被拦截）。
    passed: 是否通过安全审核的布尔标志（True 表示内容安全、合规，可以通过；False 表示存在安全风险，触发拦截或返工）。
    risk_level: 识别到的风险等级（类型为枚举 RiskLevel，例如轻微、中等、致命/严重风险）。
    risk_types: 触发的风险类型列表（默认空列表，记录具体触犯了哪些违规类型，如暴力、敏感词、版权、不当内容等）。
    findings: 详细的问题发现列表（包含多个 ReviewFinding 实例，默认空列表，记录具体的违规证据、扣分项与详细说明）。
    affected_artifacts: 受安全问题波及的产物列表（默认空列表，记录哪些剧本、分镜或资产受到了该安全问题的牵连）。
    repair_target: 建议修复的目标节点（类型为枚举 NodeId，可选。指明为了消除该安全风险，工作流应该回滚到哪一个历史节点重新生成）。
    safe_rewrite_suggestions: 安全重写/整改建议列表（默认空列表，为后续的 Agent 提供具体的合规修改方向或替换文本，以绕过风险）。
"""
class SafetyReviewReport(BaseModel):
    report_id: str
    layer: SafetyLayer
    passed: bool
    risk_level: RiskLevel
    risk_types: list[str] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)
    affected_artifacts: list[str] = Field(default_factory=list)
    repair_target: NodeId | None = None
    safe_rewrite_suggestions: list[str] = Field(default_factory=list)