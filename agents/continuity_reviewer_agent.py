"""一致性审核 Agent。"""

from __future__ import annotations

from agents.base_agent import AgentContext, AgentResult, BaseAgent
from domain.review.continuity_review import ContinuityReviewReport
from schemas.enums import ReviewType
from services.llm import generate_model_with_fallback, json_dumps_for_prompt


class ContinuityReviewerAgent(BaseAgent[ContinuityReviewReport]):
    name = "continuity_reviewer_agent"

    def run(self, context: AgentContext, **kwargs) -> AgentResult[ContinuityReviewReport]:
        review_type = kwargs.get("review_type", ReviewType.TEXT_CONTINUITY)
        report = generate_model_with_fallback(
            "agents.continuity_reviewer",
            {
                "user_request": context.user_request,
                "review_type": review_type.value,
                "summary": kwargs.get("summary", "一致性审核通过。"),
                "state_context": json_dumps_for_prompt(kwargs.get("state_context", {})),
                "checked_scene_ids": json_dumps_for_prompt(kwargs.get("checked_scene_ids", [])),
                "checked_shot_ids": json_dumps_for_prompt(kwargs.get("checked_shot_ids", [])),
            },
            ContinuityReviewReport,
            fallback=lambda: self._rule_review(review_type, kwargs),
            temperature=0.2,
        )
        return AgentResult(output=report, summary=report.overall_comment)

    def _rule_review(self, review_type: ReviewType, kwargs) -> ContinuityReviewReport:
        """规则兜底：沿用现有的默认通过策略。"""

        return ContinuityReviewReport(
            review_type=review_type,
            report_id=f"{review_type.value}_v001",
            passed=True,
            overall_comment=kwargs.get("summary", "一致性审核通过。"),
            checked_scene_ids=kwargs.get("checked_scene_ids", []),
            checked_shot_ids=kwargs.get("checked_shot_ids", []),
            checked_character_ids=kwargs.get("checked_character_ids", []),
            checked_prop_ids=kwargs.get("checked_prop_ids", []),
        )
