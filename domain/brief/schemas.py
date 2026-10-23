"""创作简报相关数据结构占位。

后续应定义 CreativeBrief、BriefValidation、AudienceProfile、PlatformProfile 等模型，
用于描述题材、类型、平台、受众、集数、单集时长、风格、禁忌点和缺失字段。
"""

# 这一阶段仍然不写 LangGraph，不写 Agent 调用，不接 LLM。目标是先把短剧制作流程里的核心数据结构固定下来，让后续所有节点都有统一输入输出格式。
# 作用：让“用户自然语言需求”被结构化成后续可消费的创作简报。

"""Creative brief domain models."""

from pydantic import BaseModel, Field


"""
创意简报
    genre / sub_genre：主分类与子分类（例如：科幻、赛博朋克）。
    platform：目标发布平台（例如：TikTok、YouTube、Netflix）。
    audience：目标受众群体。
    episode_count / episode_duration_minutes：剧集数量与单集时长。
    tone：作品基调/氛围（例如：轻松搞笑、悬疑压抑）。
    style_keywords：风格关键词列表（默认空列表）。
    story_seed：故事种子或核心创意灵感。
    constraints / forbidden_elements：创作约束条件与禁忌元素列表（用于安全过滤或合规限制）。
"""
class CreativeBrief(BaseModel):
    genre: str | None = None
    sub_genre: str | None = None
    platform: str | None = None
    audience: str | None = None
    episode_count: int | None = None
    episode_duration_minutes: float | None = None
    tone:  str | None = None
    style_keywords: list[str] = Field(default_factory=list)
    story_seed: str | None = None
    constraints: list[str] = Field(default_factory=list)
    forbidden_elements: list[str] = Field(default_factory=list)


"""
简报校验结果
    is_complete：布尔值，标识当前简报信息是否完整、是否足以进入下一步创作。
    missing_fields：缺失的关键字段列表。
    assumptions：在信息不足时，AI 自动补充的合理假设列表。
    questions_for_user：为了让简报更完善，需要向用户进一步提问的问题列表。
"""
class BriefValidation(BaseModel):
    is_complete: bool
    missing_fields: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    questions_for_user: list[str] = Field(default_factory=list)