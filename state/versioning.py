"""状态与产物版本策略占位。

用于生成版本号、追踪父子版本、记录返工链路，并支持最终交付时回溯所有产物来源。
"""

# 作用：统一 artifact 版本命名规则，避免后续到处手写 v001、v002。
from schemas.enums import ArtifactType


def format_version(version: int) -> str:
    if version < 1:
        raise ValueError("version must be at least 1")
    return f"v{version:03d}"


def build_artifact_id(artifact_type: ArtifactType, version: int, name: str | None = None) -> str:
    version_text = format_version(version)
    if name:
        return f"{artifact_type.value}_{name}_{version_text}"
    return f"{artifact_type.value}_{version_text}"