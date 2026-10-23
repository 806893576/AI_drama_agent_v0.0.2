"""剧本审核报告模型占位。

用于描述剧情逻辑、人物动机、节奏、爽点、反转、平台适配度和修改建议。
"""

# 作用：承载剧本审稿人 Agent 的输出，审核剧情逻辑、角色动机、节奏、爽点、反转和平台适配。
# 后续 script_reviewer 节点生成这个报告。如果 passed=False，就进入质量评分和返工规划。
from pydantic import BaseModel, Field

from domain.review.base import ReviewFinding
from schemas.enums import ReviewType


"""
承载剧本审稿人 Agent（Script Reviewer）的输出报告
    review_type: 审查类型（默认值为 ReviewType.SCRIPT，用于标识这是一份针对剧本的专项审核报告）。
    report_id: 报告的唯一标识符。
    passed: 是否通过审核的布尔标志（True 表示剧本合格，可以直接往下流转；False 表示未通过，触发后续的质量评分、返工规划或拦截流程）。
    overall_comment: 整体综合评价（对该剧本的宏观总结性评语）。
    findings: 发现的具体问题列表（包含多个前面定义的 ReviewFinding 实例，默认空列表，详细记录各项扣分项、风险证据与返工建议）。
    strengths: 剧本的优点/亮点列表（默认空列表，记录该剧本做得好的地方，如反转精妙、节奏紧凑等）。
    revision_notes: 修改修订意见列表（默认空列表，为编剧或润色 Agent 提供宏观或局部的整体修改指导方针）。
"""
class ScriptReviewReport(BaseModel):
    review_type: ReviewType = ReviewType.SCRIPT
    report_id: str
    passed: bool
    overall_comment: str
    findings: list[ReviewFinding] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    revision_notes: list[str] = Field(default_factory=list)