# API 设计规划

## 目标

API 层应为前端、CLI 或其他系统提供短剧方案生成能力，同时暴露流式进度、人工确认、产物查询和导出能力。

## 推荐接口

```text
POST /drama/jobs
  创建短剧生成任务。

GET /drama/jobs/{job_id}
  查询任务状态、当前阶段、最近审核结果和最终输出引用。

GET /drama/jobs/{job_id}/events
  通过 WebSocket 或 SSE 订阅 LangGraph 执行事件。

POST /drama/jobs/{job_id}/feedback
  提交用户补充需求、确认结果或修改意见。

GET /drama/jobs/{job_id}/artifacts/{artifact_id}
  查询某个长文本产物。

GET /drama/jobs/{job_id}/assets
  查询资产注册表。

POST /drama/jobs/{job_id}/export
  导出最终交付包。
```

## 状态返回建议

任务状态接口不应直接返回完整剧本或分镜长文本，而应返回 artifact 引用、摘要、当前阶段、审核结论和下一步动作。

长文本通过 artifact 查询接口单独读取。
