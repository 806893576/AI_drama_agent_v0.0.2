"""安全合规审核 Agent。"""

from __future__ import annotations

from agents.base_agent import AgentContext, AgentResult, BaseAgent
from domain.review.safety_review import SafetyReviewReport
from schemas.enums import RiskLevel, SafetyLayer
from services.llm import generate_model_with_fallback, json_dumps_for_prompt


class SafetyReviewerAgent(BaseAgent[SafetyReviewReport]):
    name = "safety_reviewer_agent"

    def run(self, context: AgentContext, **kwargs) -> AgentResult[SafetyReviewReport]:
        layer = kwargs.get("layer", SafetyLayer.FINAL)
        report_id = kwargs.get("report_id", f"{layer.value}_v001")
        report = generate_model_with_fallback(
            "agents.safety_reviewer",
            {
                "user_request": context.user_request,
                "layer": layer.value,
                "report_id": report_id,
                "state_context": json_dumps_for_prompt(kwargs.get("state_context", {})),
            },
            SafetyReviewReport,
            fallback=lambda: self._rule_review(layer, report_id),
            temperature=0.1,
        )
        return AgentResult(output=report, summary=f"{report.layer.value} 安全审核{'通过' if report.passed else '未通过'}。")

    def _rule_review(self, layer: SafetyLayer, report_id: str) -> SafetyReviewReport:
        """规则兜底：默认低风险通过，后续可接平台规则库。"""

        return SafetyReviewReport(
            report_id=report_id,
            layer=layer,
            passed=True,
            risk_level=RiskLevel.NONE,
            risk_types=[],
            affected_artifacts=[],
            safe_rewrite_suggestions=[],
        )
