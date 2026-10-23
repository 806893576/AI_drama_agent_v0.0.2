"""输入安全检查。"""

from __future__ import annotations

from domain.review.base import ReviewFinding
from domain.review.safety_review import SafetyReviewReport
from safety.policies import BLOCK_KEYWORDS, REWRITE_KEYWORDS, find_keywords
from schemas.enums import IssueType, NodeId, RiskLevel, SafetyLayer


class InputSafetyGuard:
    def check(self, user_request: str) -> SafetyReviewReport:
        text = user_request.strip()
        if not text:
            return _blocked_or_rewrite_report(
                risk_level=RiskLevel.MEDIUM,
                repair_target=NodeId.INPUT_REWRITE,
                risk_type="empty_request",
                description="用户请求为空，无法进入需求分析。",
                evidence=[],
            )

        block_hits = find_keywords(text, BLOCK_KEYWORDS)
        if block_hits:
            return _blocked_or_rewrite_report(
                risk_level=RiskLevel.HIGH,
                repair_target=NodeId.REJECT_END,
                risk_type="blocked_request",
                description=f"请求包含不能继续处理的内容：{', '.join(block_hits)}。",
                evidence=block_hits,
            )

        rewrite_hits = find_keywords(text, REWRITE_KEYWORDS)
        if rewrite_hits:
            return _blocked_or_rewrite_report(
                risk_level=RiskLevel.MEDIUM,
                repair_target=NodeId.INPUT_REWRITE,
                risk_type="rewrite_required",
                description=f"请求需要改写或澄清：{', '.join(rewrite_hits)}。",
                evidence=rewrite_hits,
            )

        return SafetyReviewReport(
            report_id="input_safety_v001",
            layer=SafetyLayer.INPUT,
            passed=True,
            risk_level=RiskLevel.LOW,
        )


def _blocked_or_rewrite_report(
    risk_level: RiskLevel,
    repair_target: NodeId,
    risk_type: str,
    description: str,
    evidence: list[str],
) -> SafetyReviewReport:
    return SafetyReviewReport(
        report_id="input_safety_v001",
        layer=SafetyLayer.INPUT,
        passed=False,
        risk_level=risk_level,
        risk_types=[risk_type],
        findings=[
            ReviewFinding(
                issue_type=IssueType.SAFETY_RISK,
                severity=risk_level,
                description=description,
                evidence=evidence,
                suggested_target_node=repair_target,
                suggested_changes=["改为原创设定，避免规避审核、复刻 IP 或涉及敏感个人信息。"],
            )
        ],
        repair_target=repair_target,
        safe_rewrite_suggestions=["请改写为原创、合规、可公开发布的短剧需求。"],
    )


def check_user_request(user_request: str) -> SafetyReviewReport:
    return InputSafetyGuard().check(user_request)
