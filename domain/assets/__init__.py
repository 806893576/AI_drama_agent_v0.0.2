"""资产管理领域对象包。

包含资产注册表、资产版本和跨产物引用关系。
"""

# 定义资产是什么、有哪些字段、如何互相引用。
# 作用：方便后续统一导入资产模型。
from domain.assets.asset_reference import AssetReference
from domain.assets.asset_registry import (
    AssetRegistry,
    BaseAsset,
    CharacterAsset,
    PromptAsset,
    PropAsset,
    SceneAsset,
    ShotAsset,
)
from domain.assets.asset_version import AssetVersion

__all__ = [
    "AssetReference",
    "AssetRegistry",
    "AssetVersion",
    "BaseAsset",
    "CharacterAsset",
    "PromptAsset",
    "PropAsset",
    "SceneAsset",
    "ShotAsset",
]