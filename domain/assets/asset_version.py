"""资产版本模型占位。

用于记录每个资产版本的来源节点、创建时间、父版本、变更原因、存储位置和审核状态。
"""

# 作用：记录一个资产的每一次版本变化。
# 例如角色 char_001 第一次由人物关系节点生成，后续美术组修改形象时产生第二版，就可以追踪：
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from schemas.enums import NodeId


"""
对具体资产（如图片、视频、3D模型、音频等媒体文件）的版本进行精细化管理和追踪
    version_id: 版本项的唯一标识符（用于区分该资产的某一个特定历史版本）。
    version: 版本号数字（默认值为 1，随着资产的不断迭代、修改或重新生成而递增）。
    created_by: 创建该资产版本的工作流节点 ID（类型为枚举 NodeId，记录是由哪个节点或 Agent 产出的）。
    source_artifact_id: 源产物 ID（可选，记录该资产是由哪一个上游产物驱动或转换而来的）。
    parent_version_id: 父级版本 ID（可选，用于构建资产的版本演进血缘树，指明它是基于哪个旧版本修改而来的）。
    change_reason: 变更的原因说明（可选，记录为什么要修改或重新生成这个资产，如“风格微调”、“画面修正”等）。
    storage_uri: 存储地址/URI（可选，指向该资产在云端存储、本地文件系统或对象存储中的实际访问路径，如 S3 链接或文件路径）。
    metadata: 扩展元数据字典（默认空字典，用于存放与该资产相关的其他技术参数、尺寸、格式、耗时等信息）。
    created_at: 创建时间戳（默认值为当前的 UTC 时间，由 lambda 动态生成，记录资产版本的生成时刻）。
"""
class AssetVersion(BaseModel):
    version_id: str
    version: int = 1
    created_by: NodeId | None = None
    source_artifact_id: str | None = None
    parent_version_id: str | None = None
    change_reason: str | None = None
    storage_uri: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))