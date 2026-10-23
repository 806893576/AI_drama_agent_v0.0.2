"""一致性审核报告模型占位。

用于检查人物关系、时间线、场景、道具、服装、镜头、声音和资产引用是否一致。
"""

# 作用：同时支持文本一致性审核和制作一致性审核。
"""Continuity review domain models."""

from pydantic import BaseModel, Field

from domain.review.base import ReviewFinding
from schemas.enums import ReviewType


"""
使用时：
text_report = ContinuityReviewReport(
    review_type=ReviewType.TEXT_CONTINUITY,
    report_id="continuity_text_v001",
    passed=True,
    overall_comment="人物关系和时间线一致。",
)
制作阶段使用：
production_report = ContinuityReviewReport(
    review_type=ReviewType.PRODUCTION_CONTINUITY,
    report_id="continuity_production_v001",
    passed=False,
    overall_comment="部分 Prompt 引用的 scene_id 不存在。",
)
具体作用：
让“一致性审核”不只是自然语言结论，而是能定位到角色、场景、道具、镜头 ID。
"""
class ContinuityReviewReport(BaseModel):
    review_type: ReviewType
    report_id: str
    passed: bool
    overall_comment: str
    findings: list[ReviewFinding] = Field(default_factory=list)
    checked_character_ids: list[str] = Field(default_factory=list)
    checked_scene_ids: list[str] = Field(default_factory=list)
    checked_prop_ids: list[str] = Field(default_factory=list)
    checked_shot_ids: list[str] = Field(default_factory=list)