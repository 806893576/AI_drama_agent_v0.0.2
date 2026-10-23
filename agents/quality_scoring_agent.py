"""质量评分 Agent。"""

from __future__ import annotations

from agents.base_agent import AgentContext, AgentResult, BaseAgent
from agents.script_reviewer_agent import _compact_episode_scripts_for_review
from domain.review.quality_score import QualityScoreReport
from services.llm import generate_model_with_fallback, json_dumps_for_prompt


class QualityScoringAgent(BaseAgent[QualityScoreReport]):
    name = "quality_scoring_agent"

    def run(self, context: AgentContext, **kwargs) -> AgentResult[QualityScoreReport]:
        script_report = kwargs.get("script_review_report")
        episode_scripts = kwargs.get("episode_scripts", [])
        report = generate_model_with_fallback(
            "agents.quality_scoring",
            {
                "user_request": context.user_request,
                "script_review_report": json_dumps_for_prompt(script_report),
                "episode_scripts": json_dumps_for_prompt(_compact_episode_scripts_for_review(episode_scripts)),
            },
            QualityScoreReport,
            fallback=lambda: self._rule_score(script_report, episode_scripts),
            temperature=0.2,
        )
        return AgentResult(output=report, summary=report.summary)

    def _rule_score(self, script_report, episode_scripts: list) -> QualityScoreReport:
        """规则兜底：输出稳定分数，便于 LangGraph 路由测试。"""

        passed = bool(script_report and script_report.passed) if script_report is not None else bool(episode_scripts)
        total_score = 88 if passed else 62
        return QualityScoreReport(
            report_id="quality_score_v001",
            passed=total_score >= 80,
            total_score=total_score,
            dimension_scores={
                "story_logic": 88 if passed else 60,
                "character_motivation": 86 if passed else 58,
                "pacing": 90 if passed else 65,
                "platform_fit": 88 if passed else 64,
            },
            weakest_dimensions=[] if passed else ["story_logic", "character_motivation"],
            summary="质量评分达到阈值。" if passed else "质量评分不足，需要返工。",
        )
