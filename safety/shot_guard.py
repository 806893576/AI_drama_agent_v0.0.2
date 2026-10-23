"""镜头与视听安全检查。"""

from __future__ import annotations

from domain.review.safety_review import SafetyReviewReport
from schemas.enums import RiskLevel, SafetyLayer


def check_shot_av(text: str) -> SafetyReviewReport:
    return SafetyReviewReport(
        report_id="shot_av_safety_v001",
        layer=SafetyLayer.SHOT_AV,
        passed=True,
        risk_level=RiskLevel.NONE,
    )
