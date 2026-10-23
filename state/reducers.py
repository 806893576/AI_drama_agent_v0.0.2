"""LangGraph State reducer 占位。

用于定义多节点写入状态时的合并策略，例如消息追加、审核报告覆盖、版本号递增和返工次数累加。
"""

# 作用：告诉 LangGraph 多个节点写同一个字段时如何合并。
from collections.abc import Mapping, Sequence
from typing import Any


"""
具体作用：
    artifact_refs：新产物引用覆盖旧引用；
    retry_counts：返工次数累加；
    events：事件追加，不覆盖历史。
"""
def merge_artifact_refs(
    current: Mapping[str, Any] | None,
    update: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(current or {})
    merged.update(update or {})
    return merged


def merge_retry_counts(
    current: Mapping[str, int] | None,
    update: Mapping[str, int] | None,
) -> dict[str, int]:
    merged = dict(current or {})
    for key, value in (update or {}).items():
        merged[key] = merged.get(key, 0) + value
    return merged


def append_events(
    current: Sequence[Any] | None,
    update: Sequence[Any] | None,
) -> list[Any]:
    return list(current or []) + list(update or [])