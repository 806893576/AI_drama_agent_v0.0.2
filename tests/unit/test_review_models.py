import pytest

from domain.review.base import ReviewFinding
from domain.review.quality_score import QualityScoreReport
from domain.review.repair_plan import RepairPlan
from domain.review.script_review import ScriptReviewReport
from schemas.enums import IssueType, NodeId, RepairScope, ReviewType, RiskLevel


def test_script_review_report_with_finding() -> None:
    finding = ReviewFinding(
        issue_type=IssueType.CHARACTER_MOTIVATION,
        severity=RiskLevel.MEDIUM,
        description="第 3 集女主行动动机不足。",
        affected_artifacts=["episode_03_script_v001"],
        suggested_target_node=NodeId.WRITER_EPISODE_SCRIPT,
        suggested_changes=["补充外部压力和心理转折。"],
    )

    report = ScriptReviewReport(
        report_id="script_review_v001",
        passed=False,
        overall_comment="剧本需要局部返工。",
        findings=[finding],
    )

    assert report.review_type == ReviewType.SCRIPT
    assert report.findings[0].suggested_target_node == NodeId.WRITER_EPISODE_SCRIPT


def test_quality_score_report_validates_score_range() -> None:
    report = QualityScoreReport(
        report_id="quality_score_v001",
        passed=True,
        total_score=86,
        dimension_scores={"story_logic": 88, "pacing": 84},
    )

    assert report.total_score == 86

    with pytest.raises(ValueError):
        QualityScoreReport(
            report_id="quality_score_v002",
            passed=False,
            total_score=120,
        )


def test_repair_plan_uses_controlled_target_node() -> None:
    plan = RepairPlan(
        repair_plan_id="repair_plan_v001",
        issue_type=IssueType.CHARACTER_MOTIVATION,
        target_node=NodeId.WRITER_EPISODE_SCRIPT,
        scope=RepairScope.PARTIAL,
        affected_artifacts=["episode_03_script_v001"],
        keep_unchanged=["story_bible_v001"],
        instructions=["只重写第 3 集女主动机相关段落。"],
        reason="角色行为缺少足够因果支撑。",
    )

    assert plan.target_node == NodeId.WRITER_EPISODE_SCRIPT
    assert plan.scope == RepairScope.PARTIAL