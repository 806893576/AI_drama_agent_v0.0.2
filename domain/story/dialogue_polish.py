"""对白润色模型与规则占位。

用于表达角色声口、口语化程度、短剧节奏、冲突密度和平台适配修改记录。
"""

# 作用：记录对白修改目标和修改结果，支持局部返工。
from pydantic import BaseModel, Field


"""
对白润色记录模型
    episode_id: 所属集数的唯一标识符，用于将润色任务定位到具体的某一集。
    scene_id: 场景的唯一标识符（可选）。如果指定了该字段，说明这是一次局部的场景级对白返工；如果为空，则可能针对整集。
    target: 润色的修改目标/意图（例如：“增强主角在冲突爆发时的情绪张力，让语气更口语化”）。
    change_summary: 变更的总结摘要（描述实际做了哪些修改或润色）。
    preserved_constraints: 在润色过程中必须保留的约束条件列表（默认空列表，例如：“必须保留前置设定的核心口头禅”、“不能改变原有的关键剧情信息”），用于防止 AI 在自由润色时违背底层规则。
"""
class DialoguePolishNote(BaseModel):
    episode_id: str
    scene_id: str | None = None
    target: str
    change_summary: str
    preserved_constraints: list[str] = Field(default_factory=list)


"""
对白润色包模型
    polish_package_id: 对白润色包的全局唯一标识符。
    notes: 润色记录列表（包含多个 DialoguePolishNote 实例，默认空列表），用于集中存储和传输各项对白修改明细。
"""
class DialoguePolishPackage(BaseModel):
    polish_package_id: str
    notes: list[DialoguePolishNote] = Field(default_factory=list)