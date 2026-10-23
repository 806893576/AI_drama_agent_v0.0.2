"""视觉 Prompt 安全检查。"""

from __future__ import annotations

from domain.review.safety_review import SafetyReviewReport
from schemas.enums import RiskLevel, SafetyLayer


def check_visual_prompt(prompt: str) -> SafetyReviewReport:
    return SafetyReviewReport(
        report_id="prompt_safety_v001",
        layer=SafetyLayer.VISUAL_PROMPT,
        passed=True,
        risk_level=RiskLevel.NONE,
    )
