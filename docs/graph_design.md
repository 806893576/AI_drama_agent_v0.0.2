# LangGraph 设计

## 主图职责

主图负责把完整短剧制作流程串起来，并在审核、返工、人机确认和最终验收处做条件路由。

推荐主流程：

```text
input_node
  -> input_guard
  -> brief_agent
  -> producer_router
  -> writer_subgraph
  -> script_reviewer
  -> quality_scoring
  -> repair_planner
  -> script_safety
  -> text_continuity_review
  -> director_subgraph
  -> audiovisual_subgraph
  -> art_agent
  -> asset_manager
  -> production_continuity_review
  -> final_safety
  -> producer_final_review
  -> final_output
```

## 子图

### Writer Subgraph

```text
story_bible
  -> story_synopsis
  -> character_bible
  -> episode_outline
  -> episode_script
  -> dialogue_polish
  -> writer_package
```

该子图必须支持局部重入。例如剧本审稿只指出第 3 集对白问题时，只进入 `episode_script` 或 `dialogue_polish`，不重写 Story Bible。

### Director Subgraph

```text
scene_breakdown
  -> shot_design
  -> performance_direction
  -> emotional_rhythm
  -> shot_intent
  -> director_package
```

该子图主要服务分镜和拍摄执行，后续制作一致性失败时可局部回到分镜或表演调度节点。

### Audiovisual Subgraph

```text
camera_plan
lighting_plan
sound_plan
vfx_plan
  -> audiovisual_package
```

摄影、灯光、声音、特效可根据同一导演方案并行生成，最终汇总为视听方案包。

### Repair Subgraph

```text
collect_review_context
  -> quality_scoring
  -> repair_planner
  -> producer_router
```

返工子图负责把审核报告转为最小修复范围和下一节点。

## 条件边

条件边应尽量读取结构化字段：

- `review_report.passed`
- `quality_score.total`
- `repair_plan.target_node`
- `repair_plan.scope`
- `safety_review.risk_level`
- `retry_count`
- `human_confirmation_required`

避免让条件边解析自然语言报告全文。
