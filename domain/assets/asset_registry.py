"""资产注册表模型占位。

用于维护角色、场景、道具、服装、声音、镜头、Prompt 和生成结果的统一 ID、版本与引用关系。
"""

# 作用：先定义所有资产的共同字段。
from pydantic import BaseModel, Field

from domain.assets.asset_reference import AssetReference
from domain.assets.asset_version import AssetVersion
from schemas.enums import AssetType


"""
所有资产都应该有：
    asset_id
    asset_type
    name
    description
    versions
    references
    metadata
这样 Asset Registry 可以统一处理不同类型资产。
"""
"""
对所有类型的资产（如角色形象、场景背景、道具、音频、视频等）进行统一的抽象与结构化建模
    asset_id: 资产的唯一标识符（全系统的资产主键，确保在整个工作流中能够精准定位该资产）。
    asset_type: 资产的类型（类型为枚举 AssetType，例如区分是角色资产、场景资产还是道具资产）。
    name: 资产的名称（可选，人类可读的资产名称，如“主角-张三”或“Cyberpunk 街头场景”）。
    description: 资产的详细描述（可选，对该资产的背景、外观或用途做文字补充）。
    tags: 资产的标签列表（默认空列表，用于对资产进行分类、检索或过滤）。
    versions: 资产的历史版本列表（包含多个前面提到的 AssetVersion 实例，默认空列表，用于追踪该资产随时间演进的所有版本记录与存储地址）。
    references: 资产的引用关系列表（包含多个 AssetReference 实例，默认空列表，记录该资产被哪些场景、镜头或剧本所引用或依赖）。
    metadata: 资产的扩展元数据字典（默认空字典，用于存放特定资产类型的自定义技术参数或附加属性）。
"""
class BaseAsset(BaseModel):
    asset_id: str
    asset_type: AssetType
    name: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    versions: list[AssetVersion] = Field(default_factory=list)
    references: list[AssetReference] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


"""
    asset_type: 固定为 AssetType.CHARACTER（角色类型）。
    role_type: 角色的定位/类型（如主角、配角）。
    voice_style: 角色的声口/音色风格。
    visual_keywords: 角色的视觉关键词列表（指导生成保持外貌一致性的角色设定）。
"""
class CharacterAsset(BaseAsset):
    asset_type: AssetType = AssetType.CHARACTER
    role_type: str | None = None
    voice_style: str | None = None
    visual_keywords: list[str] = Field(default_factory=list)


"""
    asset_type: 固定为 AssetType.SCENE（场景类型）。
    episode_id: 归属的集数 ID（可选）。
    location_id: 地点 ID（可选）。
    time_of_day: 场景发生的时间/光线环境（如清晨、夜晚）。
    character_ids: 该场景中出现的角色 ID 列表。
    prop_ids: 该场景中出现的道具 ID 列表。
"""
class SceneAsset(BaseAsset):
    asset_type: AssetType = AssetType.SCENE
    episode_id: str | None = None
    location_id: str | None = None
    time_of_day: str | None = None
    character_ids: list[str] = Field(default_factory=list)
    prop_ids: list[str] = Field(default_factory=list)


"""
    asset_type: 固定为 AssetType.PROP（道具类型）。
    owner_character_id: 道具的拥有者角色 ID（可选）。
    first_appearance_scene_id: 道具首次登场的场景 ID（可选）。
    continuity_notes: 道具的连续性/连戏注意事项列表（默认空列表，用于防止穿帮或道具细节前后不一致）。
"""
class PropAsset(BaseAsset):
    asset_type: AssetType = AssetType.PROP
    owner_character_id: str | None = None
    first_appearance_scene_id: str | None = None
    continuity_notes: list[str] = Field(default_factory=list)


"""
    asset_type: 固定为 AssetType.SHOT（镜头类型）。
    scene_id: 归属的场景 ID。
    shot_order: 镜头的顺序编号（可选）。
    character_ids: 镜头中出镜的角色 ID 列表。
    prop_ids: 镜头中出现的道具 ID 列表。
"""
class ShotAsset(BaseAsset):
    asset_type: AssetType = AssetType.SHOT
    scene_id: str
    shot_order: int | None = None
    character_ids: list[str] = Field(default_factory=list)
    prop_ids: list[str] = Field(default_factory=list)


"""
    asset_type: 固定为 AssetType.PROMPT（提示词类型）。
    prompt: 正向提示词文本。
    negative_prompt: 反向提示词文本（可选）。
    intended_use: 提示词的预期用途（可选）。
    character_ids / scene_id / prop_ids / shot_id：多维度的关联绑定 ID（用于将提示词与具体的角色、场景、道具、镜头强绑定）。
    safety_notes: 安全注意事项列表（用于风控合规审查）。
"""
class PromptAsset(BaseAsset):
    asset_type: AssetType = AssetType.PROMPT
    prompt: str
    negative_prompt: str | None = None
    intended_use: str | None = None
    character_ids: list[str] = Field(default_factory=list)
    scene_id: str | None = None
    prop_ids: list[str] = Field(default_factory=list)
    shot_id: str | None = None
    safety_notes: list[str] = Field(default_factory=list)


"""
AssetRegistry 是一个任务内的资产总表。比如 job_001 的所有角色、场景、道具、镜头、Prompt 都存在这里。
后续节点可以这样用：
    registry.upsert_character(character_asset)
    registry.upsert_scene(scene_asset)
    registry.upsert_prompt(prompt_asset)
"""
class AssetRegistry(BaseModel):
    registry_id: str
    job_id: str

    characters: dict[str, CharacterAsset] = Field(default_factory=dict)
    scenes: dict[str, SceneAsset] = Field(default_factory=dict)
    props: dict[str, PropAsset] = Field(default_factory=dict)
    shots: dict[str, ShotAsset] = Field(default_factory=dict)
    prompts: dict[str, PromptAsset] = Field(default_factory=dict)

    metadata: dict = Field(default_factory=dict)

    def upsert_character(self, asset: CharacterAsset) -> None:
        self.characters[asset.asset_id] = asset

    def upsert_scene(self, asset: SceneAsset) -> None:
        self.scenes[asset.asset_id] = asset

    def upsert_prop(self, asset: PropAsset) -> None:
        self.props[asset.asset_id] = asset

    def upsert_shot(self, asset: ShotAsset) -> None:
        self.shots[asset.asset_id] = asset

    def upsert_prompt(self, asset: PromptAsset) -> None:
        self.prompts[asset.asset_id] = asset

    """
    制作一致性审核可以快速判断：
        这个 scene_id 是否存在？
        这个 character_id 是否已经登记？
        这个 prompt_id 引用的 shot_id 是否存在？
    """
    def get_asset(self, asset_id: str) -> BaseAsset | None:
        for collection in (
            self.characters,
            self.scenes,
            self.props,
            self.shots,
            self.prompts,
        ):
            if asset_id in collection:
                return collection[asset_id]
        return None

    def has_asset(self, asset_id: str) -> bool:
        return self.get_asset(asset_id) is not None