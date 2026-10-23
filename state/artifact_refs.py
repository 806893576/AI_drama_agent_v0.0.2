"""产物引用模型占位。

用于在 Graph State 中保存 artifact_id、version、summary、producer-visible metadata，
避免把完整剧本、分镜和 Prompt 长文本直接塞进状态。
"""

# 作用：Graph State 不保存完整剧本、分镜、Prompt、审核报告，只保存这些长文本产物的引用。
from pydantic import BaseModel

from schemas.enums import ArtifactType, NodeId


"""
具体作用：
后续节点生成长文本后，不会把完整内容塞进 state，而是：
writer_package_ref = ArtifactRef(
    artifact_id="writer_package_v001",
    artifact_type=ArtifactType.WRITER_PACKAGE,
    version=1,
    summary="包含故事圣经、人物关系、分集大纲和单集剧本。",
    created_by=NodeId.WRITER_SCRIPT_PACKAGE,
)
然后只把 writer_package_ref 写入 Graph State。
"""
"""
对各类产物（Artifact）进行轻量级的引用、追踪与版本管理
    artifact_id: 产物的唯一标识符（主键，用于在全局数据库或存储系统中准确定位该产物）。
    artifact_type: 产物的类型（类型为枚举 ArtifactType，例如剧本包、分镜包、资产注册表等，用于区分产物属于哪个领域）。
    version: 产物的版本号（默认值为 1。当产物经过返工、修改或重新生成时，版本号会递增，用于实现版本控制）。
    summary: 产物的摘要说明（可选，简要描述当前版本的内容或改动亮点，方便其他节点快速了解）。
    created_by: 创建该产物的工作流节点 ID（类型为枚举 NodeId，可选。记录该产物是由哪一个节点生成的，如编剧节点或导演节点）。
    parent_artifact_id: 父级产物 ID（可选。用于记录演进血缘关系——即当前产物是由哪一个旧版本演变而来的，方便追踪修改历史）。
"""
class ArtifactRef(BaseModel):
    artifact_id: str
    artifact_type: ArtifactType
    version: int = 1
    summary: str | None = None
    created_by: NodeId | None = None
    parent_artifact_id: str | None = None


def coerce_artifact_ref(value: ArtifactRef | dict) -> ArtifactRef:
    """把 checkpoint 中的 dict 引用恢复为 ArtifactRef。"""

    if isinstance(value, ArtifactRef):
        return value
    data = dict(value)
    if isinstance(data.get("artifact_type"), str):
        data["artifact_type"] = ArtifactType(data["artifact_type"])
    if isinstance(data.get("created_by"), str):
        data["created_by"] = NodeId(data["created_by"])
    return ArtifactRef(**data)


def get_artifact_ref_id(value: ArtifactRef | dict) -> str:
    """兼容 Pydantic 引用和 JSON dict 引用，提取 artifact_id。"""

    return value.artifact_id if isinstance(value, ArtifactRef) else str(value["artifact_id"])
