"""评测执行器。"""

from __future__ import annotations

from uuid import uuid4

from database.connection import JsonDatabase
from database.models import EvaluationRecord
from evaluation.datasets import EvaluationCase
from evaluation.metrics import score_required_artifacts
from workflows.generation_workflow import run_generation


class WorkflowEvaluator:
    def evaluate_case(self, case: EvaluationCase) -> EvaluationRecord:
        result = run_generation(case.user_request, job_id=f"eval_{case.case_id}_{uuid4().hex[:8]}")
        artifact_score = score_required_artifacts(result.summary.get("artifact_ids", {}), case.expected_artifacts)
        record = EvaluationRecord(
            evaluation_id=f"evaluation_{uuid4().hex[:12]}",
            job_id=result.summary["job_id"],
            scores={"artifact_completeness": artifact_score},
            passed=artifact_score >= 1.0 and result.summary.get("final_output_ready", False),
            summary="评测通过。" if artifact_score >= 1.0 else "交付产物不完整。",
        )
        JsonDatabase().save_evaluation(record)
        return record
