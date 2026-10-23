# 执行选项 / 节点跳过策略

`ExecutionOptions` 用于控制一次短剧生成任务是否执行某些高成本节点。默认全部开启，等价于完整 v4 流程；如果只是快速产出草案，可以关闭部分审核节点以节省 token 和运行时间。

## 可配置开关

位置：`graph/execution_options.py`

| 字段 | 默认值 | 作用 |
| --- | --- | --- |
| `run_input_safety` | `true` | 输入安全审核开关，当前保留入口字段 |
| `run_script_review` | `true` | 是否执行剧本审稿人 Agent |
| `run_quality_scoring` | `true` | 是否执行质量评分器 |
| `run_script_safety` | `true` | 是否执行剧本文本安全审核 |
| `run_text_continuity` | `true` | 是否执行文本一致性审核 |
| `run_shot_av_safety` | `true` | 是否执行镜头/视听安全审核 |
| `run_prompt_safety` | `true` | 是否执行视觉 Prompt 安全审核 |
| `run_production_continuity` | `true` | 是否执行制作一致性审核 |
| `run_final_safety` | `true` | 是否执行最终安全审核 |
| `run_final_acceptance` | `true` | 是否执行制片人最终验收 |
| `skipped_reason` | `null` | 记录跳过原因，方便追踪 |

## Python 调用

```python
from graph.execution_options import ExecutionOptions
from workflows.generation_workflow import run_generation

result = run_generation(
    "都市逆袭短剧，平台抖音，12集，每集2分钟，风格强爽点、快节奏。",
    job_id="job_fast_draft",
    execution_options=ExecutionOptions.fast_draft(),
)
```

也可以只跳过某几个节点：

```python
result = run_generation(
    user_request,
    execution_options={
        "run_script_review": False,
        "run_script_safety": False,
        "run_text_continuity": False,
    },
)
```

## API 调用

```json
{
  "job_id": "job_api_fast_draft",
  "user_request": "都市逆袭短剧，平台抖音，12集，每集2分钟，风格强爽点、快节奏。",
  "execution_options": {
    "run_script_review": false,
    "run_quality_scoring": false,
    "run_script_safety": false,
    "run_text_continuity": false,
    "run_shot_av_safety": false,
    "run_prompt_safety": false,
    "run_production_continuity": false,
    "run_final_safety": false,
    "run_final_acceptance": false,
    "skipped_reason": "fast_draft"
  }
}
```

## CLI 快速草案

```powershell
python app.py --request "都市逆袭短剧，平台抖音，12集，每集2分钟。" --fast-draft
```

## 路由实现说明

跳过逻辑在 `graph/edges.py` 中完成。节点本身不判断是否跳过；如果某个节点被关闭，条件边会直接把流程路由到下一个可执行节点。这样可以保证被跳过的 Agent 不会被调用，也不会生成对应 artifact。
