"""长文本产物库服务占位。

用于保存 CreativeBrief、Story Bible、剧本、分镜、视听方案、美术 Prompt 和审核报告全文。
Graph State 应只保存这里返回的 artifact_id、version 和摘要。
"""

# 作用：ArtifactRef 是轻量引用；ArtifactEnvelope 是真正保存到磁盘的完整对象。
# 这样后续能追踪每个产物是谁生成的、从哪个版本返工来的。
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from core.settings import get_settings
from schemas.enums import ArtifactType, NodeId
from state.artifact_refs import ArtifactRef, coerce_artifact_ref, get_artifact_ref_id
from state.versioning import build_artifact_id

"""
承载产物实际完整内容（Content）及全套元数据的标准容器
    artifact_id: 产物的唯一标识符（由版本控制工具 build_artifact_id 生成）。
    job_id: 所属任务的唯一标识符（将产物与具体的生成任务/项目实例绑定）。
    artifact_type: 产物的类型（类型为枚举 ArtifactType，例如剧本包、资产注册表等）。
    version: 产物的版本号（用于追踪迭代与返工历史）。
    content: 产物的核心内容载体（类型为 Any，可以容纳任意结构化的
        Pydantic 模型、字典或数据对象，如具体的 EpisodeScript 或 StoryBible）。
    summary: 产物的摘要说明（可选，简述当前版本的内容亮点或改动）。
    created_by: 创建该产物的工作流节点 ID（类型为枚举 NodeId，记录由哪个节点产出）。
    parent_artifact_id: 父级产物 ID（可选，用于追踪血缘关系，指明是由哪个旧版本演变而来的）。
    metadata: 扩展元数据字典（默认空字典，用于存放其他自定义的辅助标签、配置或统计信息）。
    created_at: 产物的创建时间戳（默认值为当前的 UTC 时间，确保所有产物都有精确的生成时间记录）。
"""
class ArtifactEnvelope(BaseModel):
    artifact_id: str
    job_id: str
    artifact_type: ArtifactType
    version: int
    content: Any
    summary: str | None = None
    created_by: NodeId | None = None
    parent_artifact_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# 作用：让 Artifact Store 能保存 Pydantic 模型、dict、list、str 等内容。
"""
后续你可以直接保存：
    artifact_store.save(..., content=creative_brief)
也可以保存：
    artifact_store.save(..., content={"title": "..."})
"""
def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return value.dict()
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


"""
产物会保存到类似路径：
    storage/artifacts/job_001/creative_brief/creative_brief_v001.json
    storage/artifacts/job_001/writer_package/writer_package_v001.json
    storage/artifacts/job_001/repair_plan/repair_plan_v001.json
这样每个任务的产物隔离，便于查看和清理。
"""
class ArtifactStore:
    def __init__(self, root_dir: str | Path | None = None) -> None:
        self.root_dir = Path(root_dir) if root_dir else get_settings().artifact_dir

    def _artifact_dir(self, job_id: str, artifact_type: ArtifactType) -> Path:
        return self.root_dir / job_id / artifact_type.value

    def _artifact_path(self, job_id: str, artifact_type: ArtifactType, artifact_id: str) -> Path:
        return self._artifact_dir(job_id, artifact_type) / f"{artifact_id}.json"

    """
    如果已经存在：
        writer_package_v001.json
    下一次保存同类型 artifact 时，会生成：
        writer_package_v002.json
    """
    def _next_version(
        self,
        job_id: str,
        artifact_type: ArtifactType,
        name: str | None = None,
    ) -> int:
        artifact_dir = self._artifact_dir(job_id, artifact_type)
        if not artifact_dir.exists():
            return 1

        prefix = f"{artifact_type.value}_"
        if name:
            prefix = f"{artifact_type.value}_{name}_"

        versions: list[int] = []
        for path in artifact_dir.glob(f"{prefix}v*.json"):
            stem = path.stem
            version_text = stem.rsplit("_v", 1)[-1]
            if version_text.isdigit():
                versions.append(int(version_text))

        return max(versions, default=0) + 1

    """
    节点生成长文本后调用 save()，得到一个轻量 ArtifactRef，再把 ref 写回 Graph State。
    示例：
    ref = artifact_store.save(
        job_id="job_001",
        artifact_type=ArtifactType.CREATIVE_BRIEF,
        content=creative_brief,
        summary="都市逆袭短剧创作简报。",
        created_by=NodeId.BRIEF_AGENT,
    )
    """
    def save(
        self,
        job_id: str,
        artifact_type: ArtifactType,
        content: Any,
        summary: str | None = None,
        created_by: NodeId | None = None,
        parent_ref: ArtifactRef | dict | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        version = self._next_version(job_id, artifact_type, name=name)
        artifact_id = build_artifact_id(artifact_type, version, name=name)

        parent_artifact_id = get_artifact_ref_id(parent_ref) if parent_ref else None
        envelope = ArtifactEnvelope(
            artifact_id=artifact_id,
            job_id=job_id,
            artifact_type=artifact_type,
            version=version,
            content=_to_jsonable(content),
            summary=summary,
            created_by=created_by,
            parent_artifact_id=parent_artifact_id,
            metadata=metadata or {},
        )

        artifact_dir = self._artifact_dir(job_id, artifact_type)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        path = self._artifact_path(job_id, artifact_type, artifact_id)
        envelope_json = (
            envelope.model_dump_json(indent=2)
            if hasattr(envelope, "model_dump_json")
            else envelope.json(indent=2)
        )
        path.write_text(
            envelope_json,
            encoding="utf-8",
        )

        return ArtifactRef(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            version=version,
            summary=summary,
            created_by=created_by,
            parent_artifact_id=parent_artifact_id,
        )

    """
    后续节点可以根据 state 里的 ref 读取完整产物：
        brief_ref = state["artifact_refs"]["creative_brief"]
        brief_artifact = artifact_store.load(brief_ref, job_id=state["job_id"])
        brief_content = brief_artifact.content
    注意：load() 返回的是 envelope，不只是 content，
    因为很多时候你也需要 metadata、created_by、parent_artifact_id。
    """
    def load(self, ref: ArtifactRef | dict, job_id: str) -> ArtifactEnvelope:
        ref = coerce_artifact_ref(ref)
        path = self._artifact_path(job_id, ref.artifact_type, ref.artifact_id)
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        return ArtifactEnvelope(**data)

    """
    exists() 用于测试 ref 是否有效；
    list_versions() 用于回溯某类产物的所有版本。
    例如：
    versions = artifact_store.list_versions("job_001", ArtifactType.WRITER_PACKAGE)
    """
    def exists(self, ref: ArtifactRef | dict, job_id: str) -> bool:
        ref = coerce_artifact_ref(ref)
        path = self._artifact_path(job_id, ref.artifact_type, ref.artifact_id)
        return path.exists()

    def list_versions(
        self,
        job_id: str,
        artifact_type: ArtifactType,
        name: str | None = None,
    ) -> list[ArtifactRef]:
        artifact_dir = self._artifact_dir(job_id, artifact_type)
        if not artifact_dir.exists():
            return []

        prefix = f"{artifact_type.value}_"
        if name:
            prefix = f"{artifact_type.value}_{name}_"

        refs: list[ArtifactRef] = []
        for path in sorted(artifact_dir.glob(f"{prefix}v*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            refs.append(
                ArtifactRef(
                    artifact_id=data["artifact_id"],
                    artifact_type=ArtifactType(data["artifact_type"]),
                    version=data["version"],
                    summary=data.get("summary"),
                    created_by=NodeId(data["created_by"]) if data.get("created_by") else None,
                    parent_artifact_id=data.get("parent_artifact_id"),
                )
            )

        return refs
