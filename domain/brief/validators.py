"""创作简报完整性校验占位。

后续应提供需求完整性判断、字段默认值补齐、平台约束校验等纯函数，
供 Brief Agent 和 Producer Router 复用。
"""

# 作用：判断 CreativeBrief 是否足够启动编剧阶段。
from domain.brief.schemas import BriefValidation, CreativeBrief
# 作用：让 Brief Gate 的输出结构化，而不是只返回 bool。
from pydantic import BaseModel, Field
from schemas.enums import DecisionStatus, NodeId


_REQUIRED_FIELDS = [
    "genre",
    "platform",
    "episode_count",
    "episode_duration_minutes",
    "story_seed",
]


_FIELD_QUESTIONS = {
    "genre": "请补充短剧题材，例如都市逆袭、古装甜宠、悬疑反转等。",
    "platform": "请补充目标平台，例如抖音、快手、小红书、视频号等。",
    "episode_count": "请补充集数，例如 8 集、12 集、24 集。",
    "episode_duration_minutes": "请补充单集时长，例如 1 分钟、2 分钟、5 分钟。",
    "story_seed": "请补充故事简述，例如主角是谁、遇到什么冲突、想达成什么目标。",
}


"""
这一步让 Brief Gate 可以稳定判断：
    完整 -> Producer Router / Writer Subgraph
    缺失 -> Human Confirm / 用户补充需求
"""
"""
作用：正如代码注释所言，用于为后续的 Brief Gate（关口路由）提供稳定判断依据。
逻辑：
    检查简报中所有必填字段（_REQUIRED_FIELDS），看是否存在 None 或空字符串。
    如果发现缺失字段，会自动匹配对应的追问话术（_FIELD_QUESTIONS）。
    最终返回 BriefValidation 对象，标明是否完整（is_complete），并将缺失的字段及需要向用户追问的问题（questions_for_user）打包输出，
        从而决定工作流是直接进入制片总控（Producer Router），还是暂停并流转到人工确认节点（Human Confirm）向用户索取补充信息。
"""
def validate_brief(brief: CreativeBrief) -> BriefValidation:
    missing_fields: list[str] = []

    for field_name in _REQUIRED_FIELDS:
        value = getattr(brief, field_name, None)
        if value is None:
            missing_fields.append(field_name)
        elif isinstance(value, str) and not value.strip():
            missing_fields.append(field_name)

    questions = [_FIELD_QUESTIONS[field] for field in missing_fields]

    return BriefValidation(
        is_complete=not missing_fields,
        missing_fields=missing_fields,
        assumptions=[],
        questions_for_user=questions,
    )


"""
后续 Brief Gate 可以返回：
BriefGateResult(
    status=DecisionStatus.NEEDS_USER_INPUT,
    next_node=NodeId.HUMAN_CONFIRM,
    is_complete=False,
    missing_fields=["platform", "episode_count"],
    questions_for_user=["请补充目标平台。", "请补充集数。"],
    reason="创作简报缺少关键字段。",
)
Producer 或 Human Confirm 不需要重新判断缺什么，直接读这个结构。
"""
class BriefGateResult(BaseModel):
    status: DecisionStatus
    next_node: NodeId
    is_complete: bool
    missing_fields: list[str] = Field(default_factory=list)
    questions_for_user: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    reason: str


# 作用：把 BriefValidation 转成可路由的 Gate 结果。
"""
这一步把业务判断从 graph/edges.py 中抽出来，变成领域层可测试函数。
graph/edges.py 后续只读取结果，不再自己拼业务逻辑。
"""
def evaluate_brief_gate(validation: BriefValidation) -> BriefGateResult:
    if validation.is_complete:
        return BriefGateResult(
            status=DecisionStatus.PASSED,
            next_node=NodeId.PRODUCER_ROUTER,
            is_complete=True,
            missing_fields=[],
            questions_for_user=[],
            assumptions=validation.assumptions,
            reason="创作简报字段完整，可以进入制片调度。",
        )

    return BriefGateResult(
        status=DecisionStatus.NEEDS_USER_INPUT,
        next_node=NodeId.HUMAN_CONFIRM,
        is_complete=False,
        missing_fields=validation.missing_fields,
        questions_for_user=validation.questions_for_user,
        assumptions=validation.assumptions,
        reason="创作简报缺少关键字段，需要用户补充。",
    )