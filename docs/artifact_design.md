# 产物与资产设计

## Artifact Store

Artifact Store 保存长文本或结构化大对象：

- CreativeBrief
- Story Bible
- Character Bible
- Episode Outlines
- Episode Scripts
- Writer Package
- Director Package
- Audiovisual Package
- Art Package
- Review Reports
- Final Package

每个 artifact 应包含：

```text
artifact_id
job_id
type
version
parent_version
created_by
created_at
summary
content
metadata
review_status
```

## Asset Registry

Asset Registry 维护生产资产的稳定 ID：

- character_id
- scene_id
- prop_id
- costume_id
- sound_id
- shot_id
- prompt_id
- generated_asset_id

每个资产应记录来源、版本、使用位置、引用关系和审核状态。

## 关系原则

- 剧本中的人物、场景、道具应引用稳定 ID。
- 分镜应引用剧本场景 ID 和镜头 ID。
- 美术 Prompt 应引用人物/场景/道具 ID。
- 生成结果应引用 Prompt ID 和模型参数。
- 一致性审核应基于这些引用关系定位问题来源。
