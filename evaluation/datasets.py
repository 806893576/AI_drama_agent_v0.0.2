"""评测数据集。"""

from __future__ import annotations

from pydantic import BaseModel


class EvaluationCase(BaseModel):
    case_id: str
    user_request: str
    expected_artifacts: list[str]


DEFAULT_EVALUATION_CASES = [
    EvaluationCase(
        case_id="urban_reversal_short",
        user_request="都市逆袭短剧，平台抖音，12集，每集2分钟，女主被夺走公司后重新夺回主动权。",
        expected_artifacts=["writer_package", "director_package", "audiovisual_package", "art_package", "asset_registry", "final_package"],
    )
]
