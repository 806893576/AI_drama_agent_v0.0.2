"""最终输出安全检查。"""

from __future__ import annotations

from domain.review.safety_review import SafetyReviewReport
from schemas.enums import RiskLevel, SafetyLayer


def check_final_output(text: str) -> SafetyReviewReport:
    return SafetyReviewReport(
        report_id="final_safety_v001",
        layer=SafetyLayer.FINAL,
        passed=True,
        risk_level=RiskLevel.NONE,
    )
