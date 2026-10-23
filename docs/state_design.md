# 分层状态设计

## 为什么分层

短剧生成会产生大量长文本：剧本、分镜、视听方案、美术 Prompt 和审核报告。如果全部放进 LangGraph State，状态会快速膨胀，导致上下文成本高、调试困难、返工版本难追踪。

因此状态分三层：

```text
Graph State
  保存轻量运行状态、节点路由、审核状态、artifact 引用和重试次数。

Artifact Store
  保存长文本产物全文和版本。

Asset Registry
  保存角色、场景、道具、服装、声音、镜头、Prompt、生成结果的 ID、版本和引用关系。
```

## Graph State 推荐字段

```python
{
    "job_id": "...",
    "current_stage": "writer",
    "next_node": "script_reviewer",
    "user_request": "...",
    "creative_brief_ref": {"artifact_id": "brief_v1"},
    "writer_package_ref": {"artifact_id": "writer_v3"},
    "director_package_ref": {"artifact_id": "director_v1"},
    "audiovisual_package_ref": {"artifact_id": "av_v1"},
    "art_package_ref": {"artifact_id": "art_v2"},
    "asset_registry_ref": {"artifact_id": "assets_v4"},
    "last_review_ref": {"artifact_id": "review_v6"},
    "producer_decision": {"next": "writer.episode_script"},
    "repair_plan": {"target_node": "writer.dialogue_polish"},
    "retry_counts": {"writer.dialogue_polish": 1}
}
```

## Reducer 策略

- 消息和事件采用追加。
- 当前阶段和下一节点采用覆盖。
- 产物引用采用新版本覆盖旧版本，但保留父版本关系。
- 返工次数按节点累加。
- 审核报告只在 Graph State 保存最近引用，历史报告进入 Artifact Store。
