"""评测指标。"""

from __future__ import annotations


def score_required_artifacts(artifact_ids: dict[str, str], required: list[str]) -> float:
    if not required:
        return 1.0
    present = sum(1 for key in required if key in artifact_ids)
    return round(present / len(required), 4)


def score_boolean_reports(reports: list[object]) -> float:
    if not reports:
        return 0.0
    passed = sum(1 for report in reports if getattr(report, "passed", False))
    return round(passed / len(reports), 4)
