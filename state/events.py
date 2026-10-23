# 作用：记录每个节点的运行事件，用于前端进度、日志、调试和任务回放。


from datetime import datetime, timezone
from pydantic import BaseModel, Field

from schemas.enums import EventStatus, NodeId, StageId


"""
具体作用：
每个节点执行后都可以追加一个事件：
RuntimeEvent(
    event_id="evt_001",
    node_id=NodeId.BRIEF_AGENT,
    stage=StageId.BRIEF,
    status=EventStatus.COMPLETED,
    message="Creative brief generated.",
    artifact_ids=["brief_v001"],
)
"""
"""
记录和追踪工作流运行时的事件日志与状态变化
    event_id: 事件的唯一标识符（用于区分每一条独立的运行日志）。
    node_id: 触发该事件的工作流节点 ID（类型为枚举 NodeId，指明当前事件发生在哪个具体步骤，如编剧节点、分镜节点等）。
    stage: 当前事件所属的工作流大阶段（类型为枚举 StageId，例如编剧阶段、视听制作阶段）。
    status: 事件的执行状态（类型为枚举 EventStatus，例如开始执行、运行成功、运行失败、被跳过等）。
    message: 事件的详细描述信息/日志文本（说明当前节点正在做什么，或者抛出了什么错误信息）。
    artifact_ids: 关联的产物 ID 列表（默认空列表，记录当前事件创建、修改或引用了哪些具体的文件、剧本或资产）。
    created_at: 事件的创建时间戳（默认值为当前 UTC 时间，使用 datetime.now(timezone.utc) 并结合 lambda 工厂函数动态生成，确保每条日志都有准确的发生时间）。
"""
class RuntimeEvent(BaseModel):
    event_id: str
    node_id: NodeId
    stage: StageId
    status: EventStatus
    message: str
    artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))