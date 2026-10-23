"""评测系统包。"""

from evaluation.benchmarks import run_default_benchmark
from evaluation.evaluator import WorkflowEvaluator

__all__ = ["WorkflowEvaluator", "run_default_benchmark"]
