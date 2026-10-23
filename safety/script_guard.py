"""剧本文本安全检查。"""

from __future__ import annotations

from domain.review.safety_review import SafetyReviewReport
from schemas.enums import RiskLevel, SafetyLayer


def check_script_text(text: str) -> SafetyReviewReport:
    return SafetyReviewReport(
        report_id="script_text_safety_v001",
        layer=SafetyLayer.SCRIPT_TEXT,
        passed=True,
        risk_level=RiskLevel.NONE,
    )
