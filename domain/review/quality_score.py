"""Quality Scoring / 质量评分模型占位。

用于将审核结论量化为剧情逻辑、人物动机、节奏、爽点、反转、平台适配、可拍性、一致性和安全风险分数。
"""

# 作用：把审核结果量化，让 LangGraph 条件边更稳定，而不是完全依赖自然语言。
"""
具体作用：
后续条件边可以判断：
if quality_score.passed:
    return "script_safety"
return "repair_planner"
"""

from pydantic import BaseModel, Field, field_validator


"""
承载质量评分节点（Quality Scoring）的评分结果与数据统计报告。
    report_id: 评分报告的唯一标识符。
    passed: 是否达到及格线的布尔标志（标识当前产物质量是否合格，决定是否能够流转到下一个节点）。
    total_score: 总评分数（整体验收或综合得出的总分）。
    dimension_scores: 多维度评分字典（默认空字典，例如记录剧本在“剧情逻辑”、“对白生动度”、“人物塑造”等不同维度的具体得分情况，键为维度名，值为分数）。
    weakest_dimensions: 最薄弱的维度列表（默认空列表，用于指出当前产物失分最多、急需改进的几个薄弱环节）。
    threshold: 合格的及格分数线（默认值为 80 分）。
    summary: 评分的总结性评语（可选，对整体质量的文字评价）。
"""
class QualityScoreReport(BaseModel):
    report_id: str
    passed: bool
    total_score: int
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    weakest_dimensions: list[str] = Field(default_factory=list)
    threshold: int = 80
    summary: str | None = None

    @field_validator("total_score") # @field_validator 装饰器确保了分数的有效性（必须在 0 到 100 分之间）。
    @classmethod
    def validate_total_score(cls, value: int) -> int:
        if not 0 <= value <= 100:
            raise ValueError("total_score must be between 0 and 100")
        return value

    # 作用：对 dimension_scores 字典中的每一个维度分值进行范围校验。
    # 逻辑：遍历字典中的所有分值，确保任何一个维度的得分都在 0 到 100 之间，否则抛出异常。
    @field_validator("dimension_scores")
    @classmethod
    def validate_dimension_scores(cls, value: dict[str, int]) -> dict[str, int]:
        for score in value.values():
            if not 0 <= score <= 100:
                raise ValueError("dimension score must be between 0 and 100")
        return value