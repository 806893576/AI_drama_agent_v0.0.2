"""资产引用关系模型占位。

用于表达剧本、分镜、视听设计、美术 Prompt 与具体资产 ID 之间的引用关系。
"""

# 作用：表达“某个资产引用了另一个资产”或“某个产物使用了某个资产”。
from pydantic import BaseModel

from schemas.enums import AssetType


"""
后续可以表达：
    shot_001 使用 scene_001
    prompt_001 描述 char_001
    prompt_002 对应 shot_003
    prop_001 出现在 scene_002
这对制作一致性审核非常重要。
"""
class AssetReference(BaseModel):
    source_asset_id: str
    source_asset_type: AssetType
    target_asset_id: str
    target_asset_type: AssetType
    relation_type: str
    note: str | None = None