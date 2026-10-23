"""基准评测入口。"""

from __future__ import annotations

from evaluation.datasets import DEFAULT_EVALUATION_CASES
from evaluation.evaluator import WorkflowEvaluator


def run_default_benchmark() -> list[dict]:
    evaluator = WorkflowEvaluator()
    return [evaluator.evaluate_case(case).model_dump(mode="json") for case in DEFAULT_EVALUATION_CASES]
